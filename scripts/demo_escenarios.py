"""Ejecuta los escenarios de toma de decisiones del agente y escribe la
evidencia en docs/evidencia_escenarios.md (IE5/IE7).

Uso: python scripts/demo_escenarios.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from insight_trader.agent.graph import AgentResult, InsightTraderAgent
from insight_trader.agent.memory import LongTermMemory
from insight_trader.agent.planner import render_plan

OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "evidencia_escenarios.md"


def _section(title: str, setup: str, turns: list[tuple[str, str, AgentResult]]) -> str:
    out = [f"## {title}\n", f"{setup}\n"]
    for client, question, r in turns:
        out.append(f"**Cliente:** `{client}` | **Pregunta:** \"{question}\"\n")
        out.append("Herramientas ejecutadas:\n\n```")
        out += [f"{i}. {call}" for i, call in enumerate(r.herramientas, 1)]
        out.append("```\n")
        if r.plan_log:
            out.append("Decisiones de re-planificacion:\n")
            out += [f"- {entry}" for entry in r.plan_log]
            out.append("")
        out.append("Plan final:\n\n```\n" + (render_plan(r.plan_final) or "(sin tareas)") + "\n```\n")
        out.append("Respuesta:\n\n> " + r.respuesta.split("\nInforme guardado")[0].replace("\n", "\n> ") + "\n")
    return "\n".join(out)


def main() -> None:
    work = Path(tempfile.mkdtemp(prefix="insight_demo_"))

    def agent(client: str, scenario: str = "normal", memory: LongTermMemory | None = None) -> InsightTraderAgent:
        return InsightTraderAgent(client, scenario, memory or LongTermMemory(":memory:"), output_dir=work)

    sections = []

    q = "Que hago con TSLA?"
    sections.append(_section(
        "Escenario 1 - Misma pregunta, distinto perfil de riesgo",
        "Mismo activo y mismo mercado; cambia solo el cliente (moderado, tolerancia 12% vs agresivo, 30%).",
        [("constanza_fuentes", q, agent("constanza_fuentes").ask(q)),
         ("valentina_rojas", q, agent("valentina_rojas").ask(q))],
    ))

    a = agent("valentina_rojas")
    first = a.ask(q)
    a.set_scenario("shock")
    q2 = "Y ahora, con la caida del mercado?"
    sections.append(_section(
        "Escenario 2 - Condicion cambiante: shock de mercado en mitad de la conversacion",
        "Misma conversacion (thread_id). Entre turnos el entorno pasa de `normal` a `shock`. La segunda "
        "pregunta no menciona el activo: se hereda de la memoria de corto plazo, y la memoria de largo "
        "plazo aporta la recomendacion anterior para explicar el cambio.",
        [("valentina_rojas", q, first), ("valentina_rojas", q2, a.ask(q2))],
    ))

    q3 = "Que hago con BND?"
    sections.append(_section(
        "Escenario 3 - Datos de mercado desactualizados",
        "El feed de precios dejo de actualizarse hace 72 h. El agente cancela tareas que dependen del dato "
        "y se niega a recomendar operar.",
        [("diego_herrera", q3, agent("diego_herrera", "datos_desactualizados").ask(q3))],
    ))

    memory = LongTermMemory(work / "memoria.db")
    pref = "Recuerda que no quiero aumentar mi exposicion a cripto"
    agent("constanza_fuentes", memory=memory).ask(pref)
    q4 = "Que hago con ETH?"
    sections.append(_section(
        "Escenario 4 - Memoria de largo plazo entre sesiones",
        f"En una sesion previa la cliente dijo: \"{pref}\" (guardado con `guardar_preferencia`). "
        "Se crea una instancia NUEVA del agente con la misma base SQLite y se pregunta por ETH.",
        [("constanza_fuentes", q4, agent("constanza_fuentes", memory=LongTermMemory(work / "memoria.db")).ask(q4))],
    ))

    q5 = "Deberia comprar NVDA?"
    sections.append(_section(
        "Escenario 5 - Activo fuera del portafolio",
        "La validacion inicial (P1) falla y el agente cancela el resto del plan.",
        [("constanza_fuentes", q5, agent("constanza_fuentes").ask(q5))],
    ))

    q6 = "Revisa mi portafolio completo"
    sections.append(_section(
        "Escenario 6 - Revision de portafolio con priorizacion",
        "El plan recorre las posiciones de mayor a menor peso y antepone las alertas (P1) a medida que "
        "detecta activos sobre la tolerancia.",
        [("constanza_fuentes", q6, agent("constanza_fuentes").ask(q6))],
    ))

    header = (
        "# Evidencia de toma de decisiones del agente\n\n"
        "Generado automaticamente con `python scripts/demo_escenarios.py` (LLM simulado, determinista). "
        "Las reglas R0-R6 estan definidas en `src/insight_trader/agent/planner.py` y descritas en "
        "`docs/architecture.md`.\n"
    )
    OUTPUT_PATH.write_text(header + "\n" + "\n".join(sections), encoding="utf-8")
    print(f"Evidencia escrita en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
