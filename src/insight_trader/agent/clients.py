"""Alta y baja de clientes creados desde la interfaz web.

Los clientes nuevos se guardan como JSON en `config.CUSTOM_CLIENTS_DIR`
con el mismo formato que los clientes simulados base (`data/clients/`),
por lo que el agente, el RAG y el analisis los usan sin cambios.
Solo se aceptan activos que existen en el feed de mercado: sin datos de
mercado el agente no podria evaluar el riesgo de la posicion.
"""
from __future__ import annotations

import json
import re
import unicodedata

from insight_trader import config

RISK_CATEGORIES = ("conservador", "moderado", "agresivo")
# Tolerancia sugerida por perfil (coincide con los clientes base)
DEFAULT_TOLERANCE = {"conservador": 6, "moderado": 12, "agresivo": 30}
WEIGHT_SUM_TOLERANCE = 0.5  # margen por redondeo al validar que los pesos sumen 100%


def asset_catalog() -> list[dict]:
    """Activos disponibles para nuevas posiciones: los del feed de mercado,
    con nombre y clase tomados de los clientes base."""
    market = json.loads(config.MARKET_DATA_PATH.read_text(encoding="utf-8"))
    known: dict[str, dict] = {}
    for path in config.CLIENTS_DIR.glob("*.json"):
        for h in json.loads(path.read_text(encoding="utf-8"))["holdings"]:
            known.setdefault(h["ticker"], {"name": h["name"], "asset_class": h["asset_class"]})
    return [
        {
            "ticker": a["ticker"],
            "name": known.get(a["ticker"], {}).get("name", a["ticker"]),
            "asset_class": known.get(a["ticker"], {}).get("asset_class", "otro"),
            "price": a["price"],
        }
        for a in market["assets"]
    ]


def _slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")
    return slug or "cliente"


def _number(value, field: str, minimum: float, maximum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} debe ser un numero") from None
    if number < minimum or (maximum is not None and number > maximum):
        limit = f"entre {minimum} y {maximum}" if maximum is not None else f"mayor o igual a {minimum}"
        raise ValueError(f"{field} debe estar {limit}")
    return number


def create_client(data: dict) -> str:
    """Valida los datos del formulario, guarda el cliente y devuelve su id."""
    name = " ".join(str(data.get("client_name", "")).split())
    if len(name) < 3:
        raise ValueError("El nombre del cliente debe tener al menos 3 caracteres")

    category = data.get("risk_category")
    if category not in RISK_CATEGORIES:
        raise ValueError(f"Perfil de riesgo invalido. Opciones: {', '.join(RISK_CATEGORIES)}")
    tolerance = _number(data.get("max_drawdown_tolerance_pct"), "La tolerancia a drawdown", 1, 100)
    horizon = int(_number(data.get("investment_horizon_years"), "El horizonte de inversion", 1, 50))

    catalog = {a["ticker"]: a for a in asset_catalog()}
    raw_holdings = data.get("holdings") or []
    if not raw_holdings:
        raise ValueError("El cliente debe tener al menos una posicion")

    holdings, seen = [], set()
    for i, h in enumerate(raw_holdings, 1):
        ticker = str(h.get("ticker", "")).upper()
        if ticker not in catalog:
            raise ValueError(f"Posicion {i}: el activo '{ticker}' no existe en el feed de mercado")
        if ticker in seen:
            raise ValueError(f"Posicion {i}: el activo {ticker} esta repetido")
        seen.add(ticker)
        holdings.append({
            "ticker": ticker,
            "name": catalog[ticker]["name"],
            "quantity": _number(h.get("quantity"), f"Posicion {i}: la cantidad", 0.0001),
            "avg_buy_price": _number(h.get("avg_buy_price"), f"Posicion {i}: el precio promedio", 0.01),
            "current_weight_pct": _number(h.get("current_weight_pct"), f"Posicion {i}: el peso", 0.1, 100),
            "asset_class": catalog[ticker]["asset_class"],
        })

    total = sum(h["current_weight_pct"] for h in holdings)
    if abs(total - 100) > WEIGHT_SUM_TOLERANCE:
        raise ValueError(f"Los pesos del portafolio deben sumar 100% (suman {round(total, 1)}%)")

    client_id = _slug(name)
    existing = set(config.list_client_ids())
    base, n = client_id, 2
    while client_id in existing:
        client_id, n = f"{base}_{n}", n + 1

    notes = " ".join(str(data.get("notes", "")).split()) or "Cliente creado desde la interfaz web."
    record = {
        "client_id": f"CLT-WEB-{len(existing) + 1:03d}",
        "client_name": name,
        "risk_profile": {
            "category": category,
            "max_drawdown_tolerance_pct": tolerance,
            "investment_horizon_years": horizon,
            "notes": notes,
        },
        "holdings": holdings,
        "transactions": [],
    }
    config.CUSTOM_CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
    (config.CUSTOM_CLIENTS_DIR / f"{client_id}.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return client_id


def delete_client(client_id: str) -> None:
    """Elimina un cliente creado desde la web (los clientes base no se borran)."""
    if not config.is_custom_client(client_id):
        raise ValueError("Solo se pueden eliminar clientes creados desde la interfaz web")
    (config.CUSTOM_CLIENTS_DIR / f"{client_id}.json").unlink()
