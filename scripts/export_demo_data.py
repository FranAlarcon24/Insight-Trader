"""Exporta las respuestas reales del copiloto (para las posiciones del
portafolio simulado) a un JSON consumible por el frontend en React."""
import json
from pathlib import Path

from insight_trader.agents.orchestrator import TradingCopilotOrchestrator

OUTPUT_PATH = Path(__file__).parent.parent / "recommendations.json"


def main() -> None:
    orchestrator = TradingCopilotOrchestrator()
    tickers = ["TSLA", "AAPL", "ETH", "BND", "VNQ"]
    question = "Deberia mantener, comprar o vender mi posicion?"

    results = []
    for ticker in tickers:
        r = orchestrator.ask(ticker, question)
        results.append({
            "ticker": r.ticker,
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

    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado en {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
