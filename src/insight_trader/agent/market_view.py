"""Datos para los paneles de mercado de la interfaz web.

- `scenario_snapshot(escenario)`: metricas del entorno simulado que usa el
  agente, comparadas con el mercado normal, mas el impacto en cada cliente
  (que posiciones quedan sobre su tolerancia en ese escenario).
- `real_market()`: referencia de mercado real desde la API publica de Yahoo
  Finance (sin clave). Solo se muestra como contexto: el agente sigue
  trabajando con los datos simulados para que la demo sea reproducible.
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
from datetime import datetime, timezone

from insight_trader import config
from insight_trader.agent.clients import asset_catalog
from insight_trader.agent.environment import MAX_DATA_AGE_HOURS, load_environment

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1mo&interval=1d"
# Ticker del feed simulado -> simbolo en Yahoo Finance
YAHOO_SYMBOLS = {"AAPL": "AAPL", "TSLA": "TSLA", "BND": "BND", "VNQ": "VNQ", "ETH": "ETH-USD"}
REAL_CACHE_SECONDS = 600
_real_cache: dict = {"at": 0.0, "data": None}


def _first_news(news: list[dict], ticker: str) -> dict | None:
    return next((n for n in news if n["ticker"] == ticker), None)


def scenario_snapshot(scenario: str) -> dict:
    env = load_environment(scenario)
    base = load_environment("normal")
    catalog = {a["ticker"]: a for a in asset_catalog()}

    assets = []
    for asset in env.market["assets"]:
        ticker = asset["ticker"]
        normal = base.asset(ticker)
        news = _first_news(env.news, ticker)
        assets.append({
            "ticker": ticker,
            "name": catalog.get(ticker, {}).get("name", ticker),
            "asset_class": catalog.get(ticker, {}).get("asset_class", "otro"),
            "price": asset["price"],
            "change_7d_pct": asset["change_7d_pct"],
            "volatility_7d_pct": asset["volatility_7d_pct"],
            "trend": asset["trend"],
            "sentiment": news["sentiment"] if news else "neutral",
            "headline": news["headline"] if news else None,
            "normal_change_7d_pct": normal["change_7d_pct"],
            "normal_volatility_7d_pct": normal["volatility_7d_pct"],
        })

    vols = {a["ticker"]: a["volatility_7d_pct"] for a in assets}
    clients = []
    for client_id in config.list_client_ids():
        client = json.loads(config.client_data_path(client_id).read_text(encoding="utf-8"))
        tolerance = client["risk_profile"]["max_drawdown_tolerance_pct"]
        over = [h for h in client["holdings"] if vols.get(h["ticker"], 0) > tolerance]
        clients.append({
            "client_id": client_id,
            "client_name": client["client_name"],
            "risk_category": client["risk_profile"]["category"],
            "tolerance": tolerance,
            "positions_over": [
                {"ticker": h["ticker"], "weight": h["current_weight_pct"], "volatility": vols[h["ticker"]]}
                for h in over
            ],
            "weight_at_risk": round(sum(h["current_weight_pct"] for h in over), 1),
        })

    avg = lambda key: round(sum(a[key] for a in assets) / len(assets), 1)  # noqa: E731
    return {
        "escenario": scenario,
        "as_of": env.market["as_of"],
        "antiguedad_h": env.data_age_hours(),
        "datos_frescos": env.is_fresh(),
        "limite_frescura_h": MAX_DATA_AGE_HOURS,
        "fuente": env.market["source"],
        "volatilidad_promedio": avg("volatility_7d_pct"),
        "volatilidad_promedio_normal": avg("normal_volatility_7d_pct"),
        "activos": assets,
        "clientes": clients,
        "noticias": [
            {"ticker": n["ticker"], "date": n["date"], "headline": n["headline"], "sentiment": n["sentiment"]}
            for n in env.news[:8]
        ],
    }


# ------------------------------------------------------------------ mercado real

def _fetch_yahoo(symbol: str) -> dict:
    request = urllib.request.Request(YAHOO_URL.format(symbol=symbol), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=8) as response:
        chart = json.loads(response.read())["chart"]["result"][0]
    points = [
        (ts, close)
        for ts, close in zip(chart["timestamp"], chart["indicators"]["quote"][0]["close"])
        if close is not None
    ]
    if len(points) < 3:
        raise ValueError("serie insuficiente")
    return {"points": points, "currency": chart["meta"].get("currency", "USD")}


def _metrics(points: list[tuple[int, float]]) -> dict:
    last_ts, last = points[-1]
    week_ago = last_ts - 7 * 86400
    # Ultimo cierre con al menos 7 dias de antiguedad (dias habiles o corridos)
    ref = next((c for ts, c in reversed(points) if ts <= week_ago), points[0][1])
    window = [c for ts, c in points if ts > week_ago] or [last]
    window_prev = [ref] + window
    returns = [(b - a) / a for a, b in zip(window_prev, window_prev[1:])]
    mean = sum(returns) / len(returns)
    std = math.sqrt(sum((r - mean) ** 2 for r in returns) / len(returns))
    return {
        "price": round(last, 2),
        "change_7d_pct": round((last - ref) / ref * 100, 1),
        # Desviacion estandar de los retornos diarios de la ultima semana,
        # escalada a la semana (x raiz del numero de observaciones)
        "volatility_7d_pct": round(std * math.sqrt(len(returns)) * 100, 1),
        "last_close_at": datetime.fromtimestamp(last_ts, tz=timezone.utc).isoformat(),
        "series": [{"t": ts, "close": round(c, 2)} for ts, c in points],
    }


def real_market() -> dict:
    """Referencia de mercado real (Yahoo Finance), con cache de 10 minutos."""
    if _real_cache["data"] and time.time() - _real_cache["at"] < REAL_CACHE_SECONDS:
        return _real_cache["data"]

    assets, errors = [], []
    for ticker, symbol in YAHOO_SYMBOLS.items():
        try:
            data = _fetch_yahoo(symbol)
            assets.append({"ticker": ticker, "symbol": symbol, "currency": data["currency"],
                           **_metrics(data["points"])})
        except Exception as exc:  # red caida, cambio de formato, limite de la API
            errors.append(f"{ticker}: {exc}")

    result = {
        "fuente": "Yahoo Finance (API pública de gráficos, sin clave)",
        "consultado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "activos": assets,
        "errores": errors,
        "desde_cache": False,
    }
    cache_file = config.OUTPUT_DIR / "mercado_real_cache.json"
    if assets:
        _real_cache.update(at=time.time(), data=result)
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        return result
    # Sin conexion o API caida: ultimo dato guardado en disco, si existe
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        return {**cached, "desde_cache": True, "errores": errors}
    return result
