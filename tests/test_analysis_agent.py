import pytest

from insight_trader.agents.analysis_agent import AnalysisAgent


def test_flags_asset_exceeding_client_risk_tolerance():
    # ETH: volatilidad_7d_pct=24.6 > tolerancia_drawdown_pct=12
    agent = AnalysisAgent()
    signal = agent.run("ETH")
    assert signal.exceeds_risk_tolerance is True


def test_does_not_flag_low_volatility_asset():
    # BND: volatilidad_7d_pct=1.2 < tolerancia_drawdown_pct=12
    agent = AnalysisAgent()
    signal = agent.run("BND")
    assert signal.exceeds_risk_tolerance is False


def test_unknown_ticker_raises_value_error():
    agent = AnalysisAgent()
    with pytest.raises(ValueError):
        agent.run("DOES_NOT_EXIST")
