"""Pruebas del agente EP2: herramientas, memoria, planificacion adaptativa."""
import json

import pytest

from insight_trader.agent import planner
from insight_trader.agent.environment import load_environment
from insight_trader.agent.graph import InsightTraderAgent
from insight_trader.agent.market_view import scenario_snapshot
from insight_trader.agent.memory import LongTermMemory
from insight_trader.agent.recommendations import recommendations
from insight_trader.agent.tools import TOOL_GROUPS


@pytest.fixture
def make_agent(tmp_path):
    def _make(client_id="constanza_fuentes", scenario="normal", memory=None):
        return InsightTraderAgent(
            client_id=client_id,
            scenario=scenario,
            memory=memory or LongTermMemory(":memory:"),
            output_dir=tmp_path,
        )

    return _make


def _tools_called(result):
    return [call.split("(")[0] for call in result.herramientas]


# ------------------------------------------------------------ herramientas (IE1)

def test_agent_exposes_query_reasoning_and_writing_tools(make_agent):
    names = {t.name for t in make_agent().tools}
    for group, tools in TOOL_GROUPS.items():
        assert set(tools) <= names, f"faltan herramientas de {group}"


def test_writing_tools_produce_report_and_alert_files(make_agent, tmp_path):
    result = make_agent().ask("Que hago con TSLA?")

    assert result.findings["informe"] is not None
    report = open(result.findings["informe"], encoding="utf-8").read()
    assert "reducir posicion" in report
    alerts = [json.loads(line) for line in (tmp_path / "alertas.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(a["ticker"] == "TSLA" and a["severidad"] == "alta" for a in alerts)


# ------------------------------------------------------------ planificacion (IE5/IE7)

def test_initial_plan_is_prioritized_validation_first_and_report_last():
    tasks = planner.initial_plan("Que hago con TSLA?", "TSLA", [])
    order = []
    while (task := planner.next_task(tasks)) is not None:
        order.append(task["herramienta"])
        task["estado"] = planner.DONE
    assert order[0] == "consultar_portafolio"
    assert order[-1] == "generar_informe"


def test_same_question_different_risk_profile_changes_decision(make_agent):
    moderate = make_agent("constanza_fuentes").ask("Que hago con TSLA?")
    aggressive = make_agent("valentina_rojas").ask("Que hago con TSLA?")

    assert "reducir" in moderate.respuesta
    assert "registrar_alerta" in _tools_called(moderate)
    assert "mantener" in aggressive.respuesta
    assert "registrar_alerta" not in _tools_called(aggressive)


def test_market_shock_triggers_replanning_and_changes_previous_recommendation(make_agent):
    agent = make_agent("valentina_rojas")
    before = agent.ask("Que hago con TSLA?")
    agent.set_scenario("shock")
    after = agent.ask("Y ahora?")  # sin ticker: se hereda del turno anterior

    assert "mantener" in before.respuesta
    assert after.ticker == "TSLA"
    assert "reducir" in after.respuesta
    assert "CAMBIA la recomendacion anterior" in after.respuesta
    assert any(entry.startswith("R3") and "critica" in entry for entry in after.plan_log)


def test_stale_data_cancels_risk_tasks_and_blocks_trading(make_agent):
    result = make_agent("diego_herrera", scenario="datos_desactualizados").ask("Que hago con BND?")

    cancelled = [t["herramienta"] for t in result.plan_final if t["estado"] == planner.CANCELLED]
    assert {"evaluar_riesgo", "buscar_noticias"} <= set(cancelled)
    assert "no operar" in result.respuesta
    assert not result.findings["datos_confiables"]


def test_unknown_ticker_aborts_plan_without_recommending(make_agent):
    result = make_agent().ask("Deberia comprar NVDA?")

    assert _tools_called(result) == ["consultar_portafolio"]
    assert "sin recomendacion" in result.respuesta
    assert all(t["estado"] == planner.CANCELLED for t in result.plan_final[1:])


def test_portfolio_review_prioritizes_riskiest_assets(make_agent):
    result = make_agent("constanza_fuentes").ask("Revisa mi portafolio completo")

    assert result.ticker == planner.PORTFOLIO_MODE
    assert "reducir ETH, TSLA" in result.respuesta  # ETH tiene menor margen que TSLA


# ------------------------------------------------------------ memoria (IE3/IE4)

def test_short_term_memory_keeps_ticker_within_thread_only(make_agent):
    agent = make_agent()
    agent.ask("Que hago con BND?", thread_id="a")

    follow_up = agent.ask("Y si sube la volatilidad?", thread_id="a")
    other_thread = agent.ask("Y si sube la volatilidad?", thread_id="b")

    assert follow_up.ticker == "BND"
    assert other_thread.ticker is None


def test_long_term_memory_persists_across_agent_instances(make_agent, tmp_path):
    db = tmp_path / "memoria.db"
    make_agent(memory=LongTermMemory(db)).ask("Recuerda que no quiero aumentar mi exposicion a cripto")

    # Nueva instancia (simula reiniciar la aplicacion) con la misma base
    result = make_agent(memory=LongTermMemory(db)).ask("Que hago con ETH?")

    assert result.findings["restricciones"]
    assert "se respeta la preferencia" in result.respuesta
    assert any(entry.startswith("R6") for entry in result.plan_log)


def test_semantic_memory_search_ranks_same_ticker_first():
    memory = LongTermMemory(":memory:")
    memory.remember("c1", "interaccion", "Pregunta sobre AAPL: mantener posicion", ticker="AAPL")
    memory.remember("c1", "interaccion", "Pregunta sobre TSLA: reducir posicion por volatilidad", ticker="TSLA")
    memory.remember("c2", "interaccion", "Otro cliente pregunta por TSLA", ticker="TSLA")

    results = memory.search("c1", "que me recomendaste sobre la volatilidad de TSLA", ticker="TSLA")

    assert results[0].ticker == "TSLA"
    assert all(r.client_id == "c1" for r in results)


def test_shock_scenario_moves_every_asset_in_a_coherent_direction():
    normal, shock = load_environment("normal"), load_environment("shock")

    for ticker in ("AAPL", "TSLA", "ETH", "VNQ", "BND"):
        assert shock.asset(ticker) != normal.asset(ticker), f"{ticker} no cambio con el shock"
        assert shock.asset(ticker)["volatility_7d_pct"] > normal.asset(ticker)["volatility_7d_pct"]
    # Activos de riesgo caen; la renta fija sube como refugio
    assert shock.asset("TSLA")["change_7d_pct"] < 0
    assert shock.asset("VNQ")["change_7d_pct"] < normal.asset("VNQ")["change_7d_pct"]
    assert shock.asset("BND")["change_7d_pct"] > 0
    assert normal.is_fresh() and not load_environment("datos_desactualizados").is_fresh()


def test_market_snapshot_reports_client_impact_per_scenario():
    normal, shock = scenario_snapshot("normal"), scenario_snapshot("shock")
    at_risk = lambda snap, cid: next(c for c in snap["clientes"] if c["client_id"] == cid)["weight_at_risk"]  # noqa: E731

    assert shock["volatilidad_promedio"] > normal["volatilidad_promedio"]
    # Valentina (tolerancia 30%) no tiene posiciones en riesgo en mercado normal, si en el shock
    assert at_risk(normal, "valentina_rojas") == 0
    assert at_risk(shock, "valentina_rojas") > 0
    assert not scenario_snapshot("datos_desactualizados")["datos_frescos"]


def test_recommendations_match_agent_decision_and_respect_preferences(make_agent):
    memory = LongTermMemory(":memory:")
    agent = make_agent("constanza_fuentes", memory=memory)
    agent.ask("Recuerda que no quiero aumentar mi exposicion a cripto")
    tsla_answer = agent.ask("Que hago con TSLA?", thread_id="b")

    recs = recommendations("normal", memory)
    constanza = next(c for c in recs["clientes"] if c["client_id"] == "constanza_fuentes")
    by_ticker = {p["ticker"]: p for p in constanza["positions"]}

    assert by_ticker["TSLA"]["action"] in tsla_answer.respuesta  # misma regla que el agente
    assert by_ticker["ETH"]["restricted"]  # preferencia de largo plazo aplicada
    assert constanza["positions"][0]["kind"] == "reducir"  # lo urgente primero
    stale = recommendations("datos_desactualizados")
    assert stale["resumen"]["no_operar"] == stale["resumen"]["posiciones"]
