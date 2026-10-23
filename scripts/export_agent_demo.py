"""Exporta conversaciones reales del agente a web-react/src/data/agent_demo.json
para el "modo grabado" de la vista web (cuando no hay API Python
disponible, ej. en el despliegue estatico de Vercel).

Uso: python scripts/export_agent_demo.py
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from insight_trader import config
from insight_trader.agent.environment import SCENARIOS
from insight_trader.agent.graph import InsightTraderAgent
from insight_trader.agent.market_view import scenario_snapshot
from insight_trader.agent.memory import LongTermMemory
from insight_trader.agent.recommendations import recommendations
from insight_trader.agent.server import client_info, serialize_result

OUTPUT_PATH = Path(__file__).parent.parent / "web-react" / "src" / "data" / "agent_demo.json"

# (id, titulo, descripcion, cliente, [(escenario, pregunta), ...])
SCRIPTS = [
    ("shock", "Shock de mercado en plena conversación", "El mercado cambia entre una pregunta y otra.",
     "valentina_rojas", [("normal", "¿Qué hago con TSLA?"), ("shock", "¿Y ahora, con la caída del mercado?")]),
    ("perfil", "Mismo activo, perfil moderado", "TSLA para una clienta con tolerancia de 12%.",
     "constanza_fuentes", [("normal", "¿Qué hago con TSLA?")]),
    ("datos", "Datos de mercado desactualizados", "El feed de precios lleva 72 h sin actualizarse.",
     "diego_herrera", [("datos_desactualizados", "¿Qué hago con BND?")]),
    ("memoria", "Memoria de preferencias", "La clienta declara una preferencia y luego pregunta por ETH.",
     "constanza_fuentes", [("normal", "Recuerda que no quiero aumentar mi exposición a cripto"),
                           ("normal", "¿Qué hago con ETH?")]),
    ("invalido", "Activo fuera del portafolio", "Se pregunta por un activo que la clienta no tiene.",
     "constanza_fuentes", [("normal", "¿Debería comprar NVDA?")]),
    ("portafolio", "Revisión de portafolio completo", "El agente recorre todas las posiciones por prioridad.",
     "constanza_fuentes", [("normal", "Revisa mi portafolio completo")]),
]


def main() -> None:
    work = Path(tempfile.mkdtemp(prefix="insight_export_"))
    exported = []
    for script_id, title, description, client_id, turns in SCRIPTS:
        agent = InsightTraderAgent(client_id, memory=LongTermMemory(":memory:"), output_dir=work)
        recorded = []
        for scenario, question in turns:
            agent.set_scenario(scenario)
            data = serialize_result(agent.ask(question, thread_id=script_id), scenario, question)
            if data["informe"]:
                data["informe"] = f"outputs/informes/{Path(data['informe']).name}"
            data["respuesta"] = data["respuesta"].split("\nInforme guardado")[0]
            recorded.append(data)
        exported.append({"id": script_id, "titulo": title, "descripcion": description,
                         "client_id": client_id, "turnos": recorded})

    clients = [
        client_info(InsightTraderAgent(cid, memory=LongTermMemory(":memory:"), output_dir=work))
        for cid in config.list_client_ids()
    ]
    market = {scenario: scenario_snapshot(scenario) for scenario in SCENARIOS}
    recs = {scenario: recommendations(scenario) for scenario in SCENARIOS}
    OUTPUT_PATH.write_text(
        json.dumps({"clientes": clients, "guiones": exported, "mercado": market, "recomendaciones": recs}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"Modo grabado exportado a {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
