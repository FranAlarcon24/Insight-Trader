"""CLI de demostracion del copiloto de trading explicable."""
from __future__ import annotations

import argparse

from insight_trader.agents.orchestrator import TradingCopilotOrchestrator


def main() -> None:
    parser = argparse.ArgumentParser(description="Insight Trader - Copiloto de Decisiones Financieras")
    parser.add_argument("ticker", help="Ticker del activo a consultar, ej. TSLA")
    parser.add_argument(
        "--question",
        default="Deberia mantener, comprar o vender mi posicion?",
        help="Pregunta del cliente sobre el activo",
    )
    args = parser.parse_args()

    orchestrator = TradingCopilotOrchestrator()
    response = orchestrator.ask(args.ticker.upper(), args.question)

    print(f"\nPregunta: {response.question}")
    print(f"Activo: {response.ticker}\n")
    print("Fuentes internas citadas:")
    for chunk in response.internal_chunks:
        print(f"  - {chunk.text}")
    print("\nFuentes externas citadas:")
    for chunk in response.external_chunks:
        print(f"  - {chunk.text}")
    print("\nRecomendacion del copiloto:")
    print(response.recommendation)


if __name__ == "__main__":
    main()
