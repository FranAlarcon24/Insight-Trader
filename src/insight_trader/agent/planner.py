"""Planificacion y toma de decisiones adaptativa del agente (IE5).

El planificador trabaja en dos momentos:

1. `initial_plan`: a partir de la solicitud interpretada arma una lista de
   tareas priorizadas (cada tarea = una herramienta + argumentos + motivo).
2. `replan`: despues de CADA ejecucion de herramienta observa el resultado
   y ajusta el plan con reglas explicitas (agrega tareas, cancela tareas,
   cambia flags que condicionan la recomendacion final). Cada ajuste queda
   registrado en un log legible para la trazabilidad y la demo.

Prioridades (menor numero = se ejecuta antes):
  P1 critica   -> validaciones, memoria, datos base y alertas de riesgo
  P2 alta      -> evidencia principal para decidir
  P3 media     -> contexto complementario
  P4 cierre    -> escritura del informe final

Las tareas son dicts planos (no dataclasses) para que el checkpointer de
LangGraph las serialice sin configuracion adicional.
"""
from __future__ import annotations

import json
import re
import unicodedata

from insight_trader import config

PORTFOLIO_MODE = "PORTAFOLIO"

# Limite de exposicion a clases de activo de riesgo segun perfil del cliente.
RISKY_CLASSES = ("equity_tech", "crypto")
CONCENTRATION_LIMITS = {"conservador": 25.0, "moderado": 40.0, "agresivo": 70.0}

# Variacion semanal bajo la cual una alerta de riesgo se considera critica.
CRITICAL_DROP_PCT = -10.0

PREFERENCE_CUES = ("prefiero", "no quiero", "evitar", "evita ", "recuerda que", "no me interesa")
PORTFOLIO_CUES = ("portafolio", "cartera", "todas mis posiciones", "mis inversiones")
_TICKER_RE = re.compile(r"\b[A-Z]{2,5}\b")
_NOT_TICKERS = {"ETF", "USD", "CLP", "IA", "OK", "Y", "EL", "LA", "QUE", "ME", "MI", "NO", "SI"}

PENDING, DONE, CANCELLED = "pendiente", "completada", "cancelada"


# ---------------------------------------------------------------- interpretacion

# Mejora EP3 (hallazgo del analisis de registros): los clientes nombran la
# empresa o la clase de activo, no el ticker ("mis acciones de Tesla", "los
# bonos"). Sin esto el agente respondia "sin recomendacion".
TICKER_ALIASES = {
    "tesla": "TSLA", "apple": "AAPL", "ethereum": "ETH", "ether": "ETH",
    "bonos": "BND", "bono": "BND", "renta fija": "BND",
    "inmobiliario": "VNQ", "inmobiliaria": "VNQ", "bienes raices": "VNQ", "reit": "VNQ",
}


def _plain(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def extract_ticker(question: str, known_tickers: set[str]) -> str | None:
    """Detecta el activo mencionado en la pregunta. Prioriza tickers
    conocidos; si se menciona un ticker desconocido (ej. NVDA) igual lo
    devuelve para que el plan lo valide y re-planifique."""
    upper = question.upper()
    for ticker in sorted(known_tickers, key=len, reverse=True):
        if re.search(rf"\b{re.escape(ticker)}\b", upper):
            return ticker
    if config.IMPROVEMENTS_ENABLED:
        plain = _plain(question)
        for alias, ticker in sorted(TICKER_ALIASES.items(), key=lambda kv: -len(kv[0])):
            if ticker in known_tickers and re.search(rf"\b{re.escape(alias)}\b", plain):
                return ticker
    candidates = [t for t in _TICKER_RE.findall(question) if t not in _NOT_TICKERS]
    return candidates[0] if candidates else None


def is_portfolio_request(question: str) -> bool:
    q = question.lower()
    return any(cue in q for cue in PORTFOLIO_CUES)


def states_preference(question: str) -> bool:
    q = question.lower()
    return any(cue in q for cue in PREFERENCE_CUES)


# ---------------------------------------------------------------- plan

def new_findings(mode: str, ticker: str | None) -> dict:
    return {
        "modo": mode,
        "ticker": ticker,
        "datos_confiables": True,
        "posicion": {},
        "mercado": {},
        "riesgo": {},
        "noticias": {},
        "memoria": {},
        "preferencias": [],
        "restricciones": [],
        "concentracion": None,
        "alertas": [],
        "informe": None,
        "error": None,
    }


def _task(tasks: list[dict], tool: str, args: dict, priority: int, reason: str, origin: str) -> dict | None:
    """Agrega una tarea si no existe otra con la misma herramienta y args."""
    for t in tasks:
        if t["herramienta"] == tool and t["args"] == args:
            return None
    task = {
        "id": f"T{len(tasks) + 1}",
        "herramienta": tool,
        "args": args,
        "prioridad": priority,
        "motivo": reason,
        "estado": PENDING,
        "origen": origin,
    }
    tasks.append(task)
    return task


def initial_plan(question: str, ticker: str | None, holdings: list[dict]) -> list[dict]:
    tasks: list[dict] = []
    add = lambda *a: _task(tasks, *a, origin="plan_inicial")  # noqa: E731

    if states_preference(question):
        add("guardar_preferencia", {"preferencia": question}, 1,
            "El cliente declaro una preferencia: se persiste en memoria de largo plazo")

    if ticker == PORTFOLIO_MODE:
        add("recordar_memoria", {"consulta": question, "ticker": None}, 1,
            "Recuperar preferencias y recomendaciones previas del cliente")
        add("evaluar_concentracion", {}, 1,
            "Medir exposicion por clase de activo frente al perfil de riesgo")
        for h in sorted(holdings, key=lambda h: h["current_weight_pct"], reverse=True):
            add("evaluar_riesgo", {"ticker": h["ticker"]}, 2,
                f"Revisar {h['ticker']} ({h['current_weight_pct']}% del portafolio); mayor peso primero")
        add("generar_informe", {"ticker": PORTFOLIO_MODE}, 4, "Dejar registro escrito de la revision")
        return tasks

    add("consultar_portafolio", {"ticker": ticker}, 1,
        "Validar que el cliente tiene posicion en el activo antes de analizar")
    add("recordar_memoria", {"consulta": question, "ticker": ticker}, 1,
        "Recuperar recomendaciones previas y preferencias del cliente")
    add("consultar_mercado", {"ticker": ticker}, 1, "Obtener precio, volatilidad y frescura del dato")
    add("evaluar_riesgo", {"ticker": ticker}, 2, "Cruzar volatilidad del activo con la tolerancia del cliente")
    add("buscar_noticias", {"ticker": ticker}, 3, "Complementar con sentimiento de noticias recientes")
    add("generar_informe", {"ticker": ticker}, 4, "Dejar registro escrito y trazable de la recomendacion")
    return tasks


def next_task(tasks: list[dict]) -> dict | None:
    pending = [t for t in tasks if t["estado"] == PENDING]
    if not pending:
        return None
    return min(pending, key=lambda t: (t["prioridad"], int(t["id"][1:])))


def render_plan(tasks: list[dict]) -> str:
    ordered = sorted(tasks, key=lambda t: (t["estado"] != PENDING, t["prioridad"], int(t["id"][1:])))
    return "\n".join(
        f"{t['id']} [{t['estado']}] P{t['prioridad']} {t['herramienta']}({json.dumps(t['args'], ensure_ascii=False)})"
        f" - {t['motivo']}"
        for t in ordered
    )


def _mark_done(tasks: list[dict], tool: str, args: dict) -> dict | None:
    """Marca como completada la tarea pendiente que corresponde a la llamada
    ejecutada. Con un LLM real los args pueden variar levemente, por eso se
    compara por herramienta + ticker."""
    ticker = args.get("ticker")
    for t in sorted(tasks, key=lambda t: (t["prioridad"], int(t["id"][1:]))):
        if t["estado"] == PENDING and t["herramienta"] == tool and t["args"].get("ticker") == ticker:
            t["estado"] = DONE
            return t
    return None


def _cancel(tasks: list[dict], predicate, reason: str) -> list[str]:
    cancelled = []
    for t in tasks:
        if t["estado"] == PENDING and predicate(t):
            t["estado"] = CANCELLED
            t["motivo"] += f" | cancelada: {reason}"
            cancelled.append(t["id"])
    return cancelled


def _refresh_restrictions(findings: dict) -> list[str]:
    """Cruza preferencias recordadas con el activo consultado."""
    ticker = findings["ticker"]
    position = findings["posicion"].get(ticker) or {}
    asset_class = position.get("clase_activo")
    new = []
    for pref in findings["preferencias"]:
        text = pref.lower()
        applies = (ticker and ticker.lower() in text) or (
            asset_class == "crypto" and ("cripto" in text or "crypto" in text)
        )
        if applies and pref not in findings["restricciones"]:
            findings["restricciones"].append(pref)
            new.append(pref)
    return new


# ---------------------------------------------------------------- re-planificacion

def replan(tasks: list[dict], findings: dict, tool: str, args: dict, result: dict) -> list[str]:
    """Actualiza plan y hallazgos segun el resultado observado. Devuelve las
    entradas de log que explican cada decision tomada."""
    log: list[str] = []
    task = _mark_done(tasks, tool, args)
    if task is None:
        log.append(f"Accion no planificada ejecutada por el LLM: {tool}({args}); se incorpora su resultado")

    ticker = args.get("ticker") or findings["ticker"]

    # Error de invocacion (argumentos invalidos, excepcion de la herramienta):
    # no es una respuesta del dominio. Hallazgo EP3: un LLM llamo
    # consultar_portafolio({}) sin ticker y el error se interpretaba como
    # "activo fuera del portafolio" (R1), cancelando todo el plan.
    invocation_error = "error" in result and not (tool == "consultar_portafolio" and "en_portafolio" in result)
    if invocation_error:
        log.append(f"{tool} fallo ({str(result['error'])[:120]}); la tarea sigue pendiente para reintentar")
        return log

    # R4 (se evalua antes que las reglas por herramienta): cualquier
    # herramienta que reporte datos viejos degrada la decision
    if result.get("datos_frescos") is False and findings["datos_confiables"]:
        findings["datos_confiables"] = False
        ids = _cancel(tasks, lambda t: t["herramienta"] in ("evaluar_riesgo", "buscar_noticias"),
                      "datos de mercado desactualizados")
        added = _task(
            tasks, "registrar_alerta",
            {"ticker": findings["ticker"], "severidad": "media",
             "motivo": f"feed de mercado con {result.get('antiguedad_h')} h de antiguedad"},
            1, "No se puede recomendar con datos viejos: se avisa al asesor", "replanificacion",
        )
        log.append(f"R4 datos: el feed tiene {result.get('antiguedad_h')} h (> 24 h) -> se cancelan "
                   f"{', '.join(ids) or 'ninguna'}" + (f" y se agrega {added['id']} registrar_alerta" if added else "")
                   + "; la recomendacion queda en 'no operar'")

    if tool == "guardar_preferencia":
        findings["preferencias"].append(result["preferencia"])

    elif tool == "consultar_portafolio":
        if not result.get("en_portafolio"):
            findings["error"] = result.get("error") or f"El cliente no tiene posicion en {ticker}"
            ids = _cancel(tasks, lambda t: True, "activo fuera del portafolio")
            log.append(f"R1 validacion: {ticker} no esta en el portafolio -> se cancelan {', '.join(ids)} "
                       "y se responde sin recomendar")
            return log
        findings["posicion"][ticker] = result["posicion"]

    elif tool == "recordar_memoria":
        findings["memoria"] = result
        prev = result.get("recomendacion_previa")
        if prev:
            log.append(f"R2 memoria: existe recomendacion previa para {ticker} ({prev['fecha']}): "
                       "la respuesta debe indicar si la decision cambia y por que")
        for pref in result.get("preferencias", []):
            if pref not in findings["preferencias"]:
                findings["preferencias"].append(pref)

    elif tool == "consultar_mercado":
        findings["mercado"][ticker] = result

    elif tool == "evaluar_riesgo":
        findings["riesgo"][ticker] = result
        if result["excede_tolerancia"] and findings["datos_confiables"]:
            critical = result["cambio_7d_pct"] <= CRITICAL_DROP_PCT
            severity = "critica" if critical else "alta"
            added = _task(
                tasks, "registrar_alerta",
                {"ticker": ticker, "severidad": severity,
                 "motivo": f"volatilidad {result['volatilidad_7d_pct']}% supera tolerancia "
                           f"{result['tolerancia_pct']}% del cliente"},
                1, "Riesgo sobre la tolerancia: se notifica al asesor antes de seguir", "replanificacion",
            )
            if added:
                log.append(f"R3 riesgo: {ticker} excede tolerancia ({result['volatilidad_7d_pct']}% > "
                           f"{result['tolerancia_pct']}%) -> se agrega {added['id']} registrar_alerta "
                           f"(P1, severidad {severity})")
            if findings["modo"] == "activo":
                added = _task(tasks, "evaluar_concentracion", {}, 3,
                              "Medir el impacto del activo riesgoso en la exposicion total", "replanificacion")
                if added:
                    log.append(f"R3 riesgo: se agrega {added['id']} evaluar_concentracion (P3) para dimensionar "
                               "cuanto reducir")

    elif tool == "buscar_noticias":
        findings["noticias"][ticker] = result

    elif tool == "evaluar_concentracion":
        findings["concentracion"] = result
        for cls in result["clases_excedidas"]:
            added = _task(
                tasks, "registrar_alerta",
                {"ticker": PORTFOLIO_MODE, "severidad": "media",
                 "motivo": f"exposicion a {cls['clase']} {cls['peso_pct']}% supera el limite "
                           f"{result['limite_pct']}% del perfil {result['perfil']}"},
                2, "Concentracion por sobre el limite del perfil", "replanificacion",
            )
            if added:
                log.append(f"R5 concentracion: {cls['clase']} pesa {cls['peso_pct']}% (> {result['limite_pct']}%) "
                           f"-> se agrega {added['id']} registrar_alerta (P2)")

    elif tool == "registrar_alerta":
        findings["alertas"].append(result)

    elif tool == "generar_informe":
        findings["informe"] = result.get("ruta")

    for pref in _refresh_restrictions(findings):
        log.append(f"R6 preferencia: el cliente pidio '{pref}' -> la recomendacion no puede aumentar "
                   f"exposicion en {ticker}")

    return log
