"""Entorno de mercado del agente, con escenarios que simulan condiciones
cambiantes (IE5/IE7).

El agente no lee `market_data.json` directamente: consulta un
`MarketEnvironment`, que puede representar el mercado "normal" o una
variacion controlada. Asi se puede demostrar, de forma reproducible, que el
mismo cliente con la misma pregunta recibe un plan y una recomendacion
distintos cuando cambia el entorno.

Escenarios:
- normal: datos tal cual los entrega el feed simulado.
- shock: alza inesperada de tasas que mueve todo el mercado. Tecnologicas
  y cripto caen fuerte (volatilidad x1.8), el inmobiliario cae (x1.6) y la
  renta fija sube como refugio (x1.5). Cada activo recibe una noticia
  acorde (negativa o positiva).
- datos_desactualizados: el feed deja de actualizarse (as_of 72 h atras);
  el agente debe detectar que los datos no son confiables y no operar.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from insight_trader import config

SCENARIOS = ("normal", "shock", "datos_desactualizados")

# "Ahora" de la simulacion: fijo para que la demo y las pruebas sean
# reproducibles (los datos simulados son del 2026-09-10).
SIMULATION_NOW = datetime(2026, 9, 10, 15, 0, tzinfo=timezone.utc)
MAX_DATA_AGE_HOURS = 24

# Efecto del shock por clase de activo (alza inesperada de tasas):
# (factor de volatilidad, cambio semanal = f(cambio previo), tendencia,
#  sentimiento y titular de la noticia que se agrega)
SHOCK_EFFECTS = {
    "equity_tech": (1.8, lambda c: -1.2 * abs(c) - 2, "baja_fuerte", "negativo",
                    "Venta masiva arrastra a {t} en una correccion abrupta del mercado"),
    "crypto": (1.8, lambda c: -1.2 * abs(c) - 2, "baja_fuerte", "negativo",
               "Salida de capitales golpea a {t} tras el alza inesperada de tasas"),
    "real_estate": (1.6, lambda c: -abs(c) - 4, "baja", "negativo",
                    "Alza de tasas encarece el financiamiento y presiona a {t}"),
    "fixed_income": (1.5, lambda c: abs(c) + 1, "alza", "positivo",
                     "Inversionistas buscan refugio en renta fija: {t} sube"),
}
# Clase de cada ticker del feed (los JSON de mercado no la incluyen)
TICKER_CLASS = {"AAPL": "equity_tech", "TSLA": "equity_tech", "ETH": "crypto",
                "VNQ": "real_estate", "BND": "fixed_income"}


@dataclass
class MarketEnvironment:
    scenario: str
    market: dict
    news: list[dict]

    def asset(self, ticker: str) -> dict | None:
        return next((a for a in self.market["assets"] if a["ticker"] == ticker), None)

    def data_age_hours(self) -> float:
        as_of = datetime.fromisoformat(self.market["as_of"].replace("Z", "+00:00"))
        return round((SIMULATION_NOW - as_of).total_seconds() / 3600, 1)

    def is_fresh(self) -> bool:
        return self.data_age_hours() <= MAX_DATA_AGE_HOURS


def _apply_shock(market: dict, news: list[dict]) -> None:
    shock_news = []
    for asset in market["assets"]:
        effect = SHOCK_EFFECTS.get(TICKER_CLASS.get(asset["ticker"], ""))
        if effect is None:
            continue
        vol_factor, change_fn, trend, sentiment, headline = effect
        asset["volatility_7d_pct"] = round(asset["volatility_7d_pct"] * vol_factor, 1)
        asset["change_7d_pct"] = round(change_fn(asset["change_7d_pct"]), 1)
        asset["trend"] = trend
        shock_news.append({
            "id": f"shock-{asset['ticker']}",
            "ticker": asset["ticker"],
            "date": "2026-09-10",
            "headline": headline.format(t=asset["ticker"]),
            "sentiment": sentiment,
            "summary": "Alza inesperada de tasas reordena los flujos: salen capitales de activos de "
                       "riesgo y entran a renta fija.",
        })
    # Las noticias del shock van primero: el analisis toma la mas reciente.
    news[:0] = shock_news


def load_environment(scenario: str = "normal") -> MarketEnvironment:
    if scenario not in SCENARIOS:
        raise ValueError(f"Escenario desconocido '{scenario}'. Opciones: {', '.join(SCENARIOS)}")
    market = json.loads(config.MARKET_DATA_PATH.read_text(encoding="utf-8"))
    news = json.loads(config.NEWS_PATH.read_text(encoding="utf-8"))
    market, news = copy.deepcopy(market), copy.deepcopy(news)

    if scenario == "shock":
        _apply_shock(market, news)
    elif scenario == "datos_desactualizados":
        stale = SIMULATION_NOW - timedelta(hours=72)
        market["as_of"] = stale.strftime("%Y-%m-%dT%H:%M:%SZ")

    return MarketEnvironment(scenario, market, news)
