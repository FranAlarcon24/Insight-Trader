from insight_trader.agents.orchestrator import TradingCopilotOrchestrator


def test_orchestrator_produces_grounded_recommendation_for_high_volatility_asset():
    orchestrator = TradingCopilotOrchestrator()
    response = orchestrator.ask("ETH", "Deberia mantener mi posicion?")

    assert response.signal.exceeds_risk_tolerance is True
    assert "reducir" in response.recommendation.lower()
    # La recomendacion debe citar el numero de volatilidad usado en el analisis
    assert str(response.signal.market_volatility_7d_pct) in response.recommendation


def test_orchestrator_cites_internal_and_external_sources():
    orchestrator = TradingCopilotOrchestrator()
    response = orchestrator.ask("AAPL", "Que hago con AAPL?")

    assert len(response.internal_chunks) > 0
    assert len(response.external_chunks) > 0
    assert all(chunk.source == "internal" for chunk in response.internal_chunks)
    assert all(chunk.source == "external" for chunk in response.external_chunks)


def test_orchestrator_recommends_maintain_for_stable_low_risk_asset():
    orchestrator = TradingCopilotOrchestrator()
    response = orchestrator.ask("BND", "Que hago con BND?")

    assert response.signal.exceeds_risk_tolerance is False
    assert "mantener" in response.recommendation.lower()
