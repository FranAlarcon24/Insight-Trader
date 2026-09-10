"""Exporta las respuestas reales del copiloto (para cada cliente simulado y
sus posiciones) a un JSON consumible por el frontend en React."""
import json
from pathlib import Path

from insight_trader import config
from insight_trader.agents.orchestrator import TradingCopilotOrchestrator

OUTPUT_PATH = Path(__file__).parent.parent / "recommendations.json"
QUESTION = "Deberia mantener, comprar o vender mi posicion?"


def export_client(client_id: str) -> dict:
    orchestrator = TradingCopilotOrchestrator(client_id=client_id)
    client = json.loads(config.client_data_path(client_id).read_text(encoding="utf-8"))

    holdings = []
    for holding in client["holdings"]:
        r = orchestrator.ask(holding["ticker"], QUESTION)
        holdings.append({
            "ticker": r.ticker,
            "name": holding["name"],
            "weight": holding["current_weight_pct"],
            "asset_class": holding["asset_class"],
            "question": r.question,
            "internal": [c.text for c in r.internal_chunks],
            "external": [c.text for c in r.external_chunks],
            "recommendation": r.recommendation,
            "signal": {
                "risk_category": r.signal.risk_category,
                "risk_tolerance": r.signal.risk_tolerance_drawdown_pct,
                "volatility": r.signal.market_volatility_7d_pct,
                "change": r.signal.market_change_7d_pct,
                "trend": r.signal.market_trend,
                "sentiment": r.signal.news_sentiment,
                "exceeds": r.signal.exceeds_risk_tolerance,
            },
        })

    return {
        "client_id": client_id,
        "client_name": client["client_name"],
        "risk_category": client["risk_profile"]["category"],
        "risk_tolerance": client["risk_profile"]["max_drawdown_tolerance_pct"],
        "investment_horizon_years": client["risk_profile"]["investment_horizon_years"],
        "notes": client["risk_profile"]["notes"],
        "holdings": holdings,
    }


def main() -> None:
    results = [export_client(client_id) for client_id in config.list_client_ids()]
    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado en {OUTPUT_PATH} ({len(results)} clientes)")


if __name__ == "__main__":
    main()
