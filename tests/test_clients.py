"""Pruebas del alta de clientes desde la interfaz web."""
import pytest

from insight_trader import config
from insight_trader.agent import clients
from insight_trader.agent.graph import InsightTraderAgent
from insight_trader.agent.memory import LongTermMemory


@pytest.fixture(autouse=True)
def custom_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CUSTOM_CLIENTS_DIR", tmp_path / "clientes")
    return tmp_path / "clientes"


def _form(**overrides):
    data = {
        "client_name": "Martina Soto",
        "risk_category": "conservador",
        "max_drawdown_tolerance_pct": 6,
        "investment_horizon_years": 4,
        "notes": "Prioriza liquidez",
        "holdings": [
            {"ticker": "ETH", "quantity": 1, "avg_buy_price": 2000, "current_weight_pct": 30},
            {"ticker": "BND", "quantity": 100, "avg_buy_price": 72, "current_weight_pct": 70},
        ],
    }
    data.update(overrides)
    return data


def test_created_client_is_listed_and_usable_by_the_agent(tmp_path):
    client_id = clients.create_client(_form())

    assert client_id == "martina_soto"
    assert client_id in config.list_client_ids()
    agent = InsightTraderAgent(client_id, memory=LongTermMemory(":memory:"), output_dir=tmp_path)
    result = agent.ask("Que hago con ETH?")
    # ETH tiene 24.6% de volatilidad: excede la tolerancia de 6% del cliente nuevo
    assert "reducir" in result.respuesta
    assert any(a["ticker"] == "ETH" for a in result.findings["alertas"])


def test_duplicate_names_get_unique_ids():
    first = clients.create_client(_form())
    second = clients.create_client(_form())
    assert first != second


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"client_name": "Al"}, "nombre"),
        ({"risk_category": "temerario"}, "Perfil"),
        ({"max_drawdown_tolerance_pct": 0}, "tolerancia"),
        ({"holdings": []}, "al menos una posicion"),
        ({"holdings": [{"ticker": "NVDA", "quantity": 1, "avg_buy_price": 1, "current_weight_pct": 100}]}, "NVDA"),
        ({"holdings": [{"ticker": "BND", "quantity": 1, "avg_buy_price": 1, "current_weight_pct": 60}]}, "100%"),
    ],
)
def test_invalid_forms_are_rejected(overrides, message):
    with pytest.raises(ValueError, match=message):
        clients.create_client(_form(**overrides))


def test_only_custom_clients_can_be_deleted():
    client_id = clients.create_client(_form())
    clients.delete_client(client_id)
    assert client_id not in config.list_client_ids()
    with pytest.raises(ValueError):
        clients.delete_client("constanza_fuentes")
