"""Vista consolidada de recomendaciones: la accion sugerida para cada
posicion de cada cliente en un escenario de mercado.

Reutiliza la misma regla de decision del agente (`llm.decide`) y la misma
logica de preferencias (`planner._refresh_restrictions`), armando los
hallazgos que el agente obtendria con sus herramientas, pero sin ejecutar
el grafo: no genera alertas, informes ni recuerdos (es solo lectura).
"""
from __future__ import annotations

import json

from insight_trader import config
from insight_trader.agent import planner
from insight_trader.agent.environment import load_environment
from insight_trader.agent.llm import decide
from insight_trader.agent.memory import LongTermMemory
from insight_trader.agents.analysis_agent import AnalysisAgent

# Orden de urgencia para el asesor (menor = primero)
_URGENCY = (("reducir", 0), ("no operar", 1), ("mantener posicion y monitorear", 2), ("mantener", 3))


def _urgency(action: str) -> int:
    return next((rank for prefix, rank in _URGENCY if action.startswith(prefix)), 4)


def _kind(action: str) -> str:
    if action.startswith("reducir"):
        return "reducir"
    if action.startswith("no operar"):
        return "no_operar"
    if "monitorear" in action:
        return "monitorear"
    return "mantener"


def recommendations(scenario: str, memory: LongTermMemory | None = None) -> dict:
    env = load_environment(scenario)
    clients = []
    for client_id in config.list_client_ids():
        client = json.loads(config.client_data_path(client_id).read_text(encoding="utf-8"))
        analysis = AnalysisAgent(client_id, market=env.market, news=env.news)
        prefs = [p.content for p in memory.preferences(client_id)] if memory else []

        positions = []
        for h in client["holdings"]:
            ticker = h["ticker"]
            signal = analysis.run(ticker)
            findings = planner.new_findings("activo", ticker)
            findings["datos_confiables"] = env.is_fresh()
            findings["posicion"][ticker] = {"clase_activo": h["asset_class"]}
            findings["mercado"][ticker] = {"antiguedad_h": env.data_age_hours()}
            findings["riesgo"][ticker] = {
                "excede_tolerancia": signal.exceeds_risk_tolerance,
                "volatilidad_7d_pct": signal.market_volatility_7d_pct,
                "tolerancia_pct": signal.risk_tolerance_drawdown_pct,
                "margen_pct": round(signal.risk_tolerance_drawdown_pct - signal.market_volatility_7d_pct, 1),
                "cambio_7d_pct": signal.market_change_7d_pct,
                "sentimiento": signal.news_sentiment,
            }
            findings["preferencias"] = list(prefs)
            planner._refresh_restrictions(findings)
            action, justification = decide(findings)
            positions.append({
                "ticker": ticker,
                "name": h["name"],
                "weight": h["current_weight_pct"],
                "volatility": signal.market_volatility_7d_pct,
                "change_7d_pct": signal.market_change_7d_pct,
                "sentiment": signal.news_sentiment,
                "action": action,
                "kind": _kind(action),
                "justification": justification,
                "restricted": bool(findings["restricciones"]),
            })
        positions.sort(key=lambda p: (_urgency(p["action"]), -p["weight"]))
        clients.append({
            "client_id": client_id,
            "client_name": client["client_name"],
            "risk_category": client["risk_profile"]["category"],
            "tolerance": client["risk_profile"]["max_drawdown_tolerance_pct"],
            "positions": positions,
            "urgent": sum(p["kind"] == "reducir" for p in positions),
        })

    clients.sort(key=lambda c: (-c["urgent"], c["client_name"]))
    all_positions = [p for c in clients for p in c["positions"]]
    count = lambda kind: sum(p["kind"] == kind for p in all_positions)  # noqa: E731
    return {
        "escenario": scenario,
        "datos_frescos": env.is_fresh(),
        "resumen": {
            "posiciones": len(all_positions),
            "reducir": count("reducir"),
            "no_operar": count("no_operar"),
            "monitorear": count("monitorear"),
            "mantener": count("mantener"),
        },
        "clientes": clients,
    }
