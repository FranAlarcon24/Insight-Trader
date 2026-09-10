"""Agente de analisis: cruza el perfil de riesgo del cliente con las
condiciones de mercado y el sentimiento de noticias para el activo
consultado, produciendo senales estructuradas que el agente generador
usara para justificar la recomendacion."""
from __future__ import annotations

import json
from dataclasses import dataclass

from insight_trader import config


@dataclass
class RiskMarketSignal:
    ticker: str
    risk_category: str
    risk_tolerance_drawdown_pct: float
    market_volatility_7d_pct: float
    market_change_7d_pct: float
    market_trend: str
    news_sentiment: str
    exceeds_risk_tolerance: bool


class AnalysisAgent:
    def __init__(self, client_id: str = config.DEFAULT_CLIENT_ID):
        self.client_id = client_id
        self._client = json.loads(config.client_data_path(client_id).read_text(encoding="utf-8"))
        self._market = json.loads(config.MARKET_DATA_PATH.read_text(encoding="utf-8"))
        self._news = json.loads(config.NEWS_PATH.read_text(encoding="utf-8"))

    def run(self, ticker: str) -> RiskMarketSignal:
        risk = self._client["risk_profile"]

        held_tickers = {h["ticker"] for h in self._client["holdings"]}
        if ticker not in held_tickers:
            raise ValueError(
                f"El cliente '{self._client['client_name']}' no tiene posicion en '{ticker}'"
            )

        asset = next((a for a in self._market["assets"] if a["ticker"] == ticker), None)
        if asset is None:
            raise ValueError(f"No hay datos de mercado para el ticker '{ticker}'")

        news_items = [n for n in self._news if n["ticker"] == ticker]
        sentiment = news_items[0]["sentiment"] if news_items else "neutral"

        exceeds_tolerance = asset["volatility_7d_pct"] > risk["max_drawdown_tolerance_pct"]

        return RiskMarketSignal(
            ticker=ticker,
            risk_category=risk["category"],
            risk_tolerance_drawdown_pct=risk["max_drawdown_tolerance_pct"],
            market_volatility_7d_pct=asset["volatility_7d_pct"],
            market_change_7d_pct=asset["change_7d_pct"],
            market_trend=asset["trend"],
            news_sentiment=sentiment,
            exceeds_risk_tolerance=exceeds_tolerance,
        )
