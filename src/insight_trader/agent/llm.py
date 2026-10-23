"""Modelo de lenguaje del agente (chat + tool calling).

Dos implementaciones con el mismo contrato de LangChain (`BaseChatModel`
con `bind_tools`), intercambiables por la variable de entorno
`INSIGHT_TRADER_LLM_PROVIDER`:

- `ScriptedToolCallingLLM` (por defecto): LLM simulado, offline y
  determinista. Lee el MISMO prompt de sistema que recibiria un LLM real
  (plan + hallazgos), llama la siguiente herramienta pendiente del plan y,
  cuando no quedan tareas, redacta la respuesta citando los hallazgos. Hace
  la demo y las pruebas reproducibles y sin costo.
- `ChatAnthropic` (Claude) via `langchain-anthropic`, activable con
  `INSIGHT_TRADER_LLM_PROVIDER=anthropic` y `ANTHROPIC_API_KEY`.
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from insight_trader import config
from insight_trader.agent.planner import PORTFOLIO_MODE

SYSTEM_PROMPT = """Eres Insight Trader, un agente copiloto de inversiones para asesores \
de una fintech. Atiendes al cliente {client_name} (perfil {risk_category}, \
tolerancia a drawdown {risk_tolerance}%). Escenario de mercado activo: {scenario}.

Reglas:
1. Sigue el PLAN: ejecuta las tareas pendientes en orden de prioridad (P1 antes \
que P2...) llamando a la herramienta indicada con esos argumentos. El plan se \
actualiza solo despues de cada herramienta; no repitas tareas completadas.
2. No inventes cifras: usa solo los datos de HALLAZGOS y de los resultados de \
herramientas, y cita los numeros concretos.
3. Si datos_confiables es false, no recomiendes operar: recomienda mantener \
sin cambios hasta contar con datos actualizados.
4. Si hay restricciones del cliente, la recomendacion no puede contradecirlas.
5. Si el activo excede la tolerancia, prioriza preservar capital (reducir).
6. Si hay una recomendacion previa en memoria, indica si cambia y por que.
7. Para generar_informe redacta tu mismo `recomendacion` y `justificacion`.
8. Cuando no queden tareas pendientes, responde al cliente en espanol, breve, \
con la recomendacion, su justificacion y las alertas registradas.

<plan>
{plan}
</plan>

<hallazgos>
{findings}
</hallazgos>
"""

_PLAN_RE = re.compile(r"<plan>\n(.*?)\n</plan>", re.S)
_FINDINGS_RE = re.compile(r"<hallazgos>\n(.*?)\n</hallazgos>", re.S)
_PENDING_RE = re.compile(r"^(T\d+) \[pendiente\] P\d (\w+)\((\{.*?\})\) - ", re.M)


# ---------------------------------------------------------------- decision

def decide(findings: dict) -> tuple[str, str]:
    """Regla de decision usada por el LLM simulado para redactar la
    recomendacion (un LLM real la deriva de las reglas del prompt)."""
    ticker = findings["ticker"]
    if findings["error"]:
        return "sin recomendacion", f"{findings['error']}. Solo se analizan activos del portafolio del cliente."

    if ticker == PORTFOLIO_MODE:
        return _decide_portfolio(findings)

    market = findings["mercado"].get(ticker, {})
    risk = findings["riesgo"].get(ticker)
    reasons: list[str] = []

    if not findings["datos_confiables"]:
        action = "no operar: mantener la posicion sin cambios hasta contar con datos actualizados"
        reasons.append(f"el feed de mercado tiene {market.get('antiguedad_h')} h de antiguedad (limite 24 h), "
                       "por lo que cualquier decision se basaria en precios que ya no son reales")
    elif risk and risk["excede_tolerancia"]:
        action = "reducir posicion"
        reasons.append(f"la volatilidad a 7 dias ({risk['volatilidad_7d_pct']}%) supera la tolerancia "
                       f"del cliente ({risk['tolerancia_pct']}%) por {abs(risk['margen_pct'])} puntos")
        if risk["cambio_7d_pct"] < 0:
            reasons.append(f"el precio cae {risk['cambio_7d_pct']}% en 7 dias con sentimiento {risk['sentimiento']}")
    elif risk and risk["cambio_7d_pct"] > 5 and risk["sentimiento"] == "positivo":
        action = "mantener posicion"
        reasons.append(f"tendencia positiva ({risk['cambio_7d_pct']}% en 7 dias) con noticias positivas y "
                       f"volatilidad ({risk['volatilidad_7d_pct']}%) dentro de la tolerancia ({risk['tolerancia_pct']}%)")
    elif risk and risk["cambio_7d_pct"] < -2:
        action = "mantener posicion y monitorear"
        reasons.append(f"caida reciente ({risk['cambio_7d_pct']}% en 7 dias) dentro de la tolerancia al riesgo")
    else:
        action = "mantener posicion"
        if risk:
            reasons.append(f"volatilidad {risk['volatilidad_7d_pct']}% dentro de la tolerancia "
                           f"({risk['tolerancia_pct']}%) y cambio semanal {risk['cambio_7d_pct']}%")

    if findings["restricciones"] and action.startswith("mantener"):
        action += " sin aumentar exposicion"
    for pref in findings["restricciones"]:
        reasons.append(f"se respeta la preferencia registrada del cliente: \"{pref}\"")

    conc = findings["concentracion"]
    if conc and conc["clases_excedidas"]:
        cls = conc["clases_excedidas"][0]
        reasons.append(f"ademas el portafolio tiene {cls['peso_pct']}% en {cls['clase']} "
                       f"(limite {conc['limite_pct']}% para perfil {conc['perfil']})")

    prev = (findings["memoria"] or {}).get("recomendacion_previa")
    if prev and prev.get("accion"):
        if prev["accion"] != action:
            reasons.append(f"esto CAMBIA la recomendacion anterior ('{prev['accion']}', {prev['fecha']}) "
                           "porque las condiciones observadas son distintas")
        else:
            reasons.append(f"se mantiene la recomendacion anterior ('{prev['accion']}', {prev['fecha']})")
    return action, "; ".join(reasons) + "."


def _decide_portfolio(findings: dict) -> tuple[str, str]:
    if not findings["datos_confiables"]:
        return ("no operar: revisar el portafolio cuando el feed de mercado este actualizado",
                "los datos de mercado estan desactualizados, por lo que no se evaluo el riesgo por activo.")
    risky = [r for r in findings["riesgo"].values() if r["excede_tolerancia"]]
    risky.sort(key=lambda r: r["margen_pct"])
    reasons = []
    if risky:
        action = "reducir " + ", ".join(r["ticker"] for r in risky) + " (en ese orden de prioridad)"
        reasons += [f"{r['ticker']}: volatilidad {r['volatilidad_7d_pct']}% vs tolerancia {r['tolerancia_pct']}%"
                    for r in risky]
    else:
        action = "mantener el portafolio sin cambios"
        reasons.append("ningun activo supera la tolerancia al riesgo del cliente")
    conc = findings["concentracion"]
    if conc:
        for cls in conc["clases_excedidas"]:
            reasons.append(f"exposicion a {cls['clase']} {cls['peso_pct']}% sobre el limite {conc['limite_pct']}%")
    return action, "; ".join(reasons) + "."


def compose_answer(findings: dict) -> str:
    if findings["ticker"] is None:
        if findings["preferencias"]:
            return ("Preferencia registrada en tu memoria de largo plazo: "
                    f"\"{findings['preferencias'][-1]}\". La aplicare en las proximas recomendaciones.")
        return "No identifique un activo en tu pregunta. Indica un ticker de tu portafolio o pide revisar tu portafolio."
    action, justification = decide(findings)
    subject = "tu portafolio" if findings["ticker"] == PORTFOLIO_MODE else findings["ticker"]
    lines = [f"Recomendacion para {subject}: {action}.", f"Justificacion: {justification}"]
    if findings["alertas"]:
        lines.append("Alertas registradas para tu asesor: " + "; ".join(
            f"[{a['severidad']}] {a['ticker']}: {a['motivo']}" for a in findings["alertas"]))
    if findings["informe"]:
        lines.append(f"Informe guardado en: {findings['informe']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- LLM simulado

class ScriptedToolCallingLLM(BaseChatModel):
    """LLM simulado con tool calling. Ver docstring del modulo."""

    @property
    def _llm_type(self) -> str:
        return "scripted-tool-calling"

    def bind_tools(self, tools: list, **kwargs: Any) -> "ScriptedToolCallingLLM":
        return self

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        system = next(m.content for m in messages if isinstance(m, SystemMessage))
        plan = _PLAN_RE.search(system).group(1)
        findings = json.loads(_FINDINGS_RE.search(system).group(1))

        pending = _PENDING_RE.search(plan)  # el plan viene ordenado por prioridad
        if pending:
            task_id, tool_name, raw_args = pending.groups()
            args = json.loads(raw_args)
            if tool_name == "generar_informe":
                args["recomendacion"], args["justificacion"] = decide(findings)
            message = AIMessage(
                content="",
                tool_calls=[{"name": tool_name, "args": args, "id": f"call_{task_id}", "type": "tool_call"}],
            )
        else:
            message = AIMessage(content=compose_answer(findings))
        return ChatResult(generations=[ChatGeneration(message=message)])


def get_chat_model(provider: str | None = None) -> BaseChatModel:
    provider = provider or config.LLM_PROVIDER
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic  # dependencia opcional

        return ChatAnthropic(model=config.ANTHROPIC_MODEL, temperature=0, max_tokens=1024)
    return ScriptedToolCallingLLM()
