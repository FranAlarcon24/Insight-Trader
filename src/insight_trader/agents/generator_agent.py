"""Agente generador: construye el prompt final combinando las fuentes
recuperadas (RAG) y la senal de analisis riesgo-mercado, y produce la
recomendacion en lenguaje natural citando los datos concretos que la
respaldan (ver docs/prompts.md para la justificacion del diseno del
prompt)."""
from __future__ import annotations

from insight_trader.agents.analysis_agent import RiskMarketSignal
from insight_trader.llm import BaseLLM
from insight_trader.rag.retriever import RetrievedChunk

PROMPT_TEMPLATE = """Eres el copiloto de trading explicable de una fintech. Tu tarea es \
recomendar comprar, vender o mantener un activo para un cliente especifico, \
citando siempre los datos concretos que respaldan la recomendacion. Nunca \
inventes cifras: usa solo los datos entregados abajo.

Activo objetivo: {ticker}

--- Contexto interno (portafolio, perfil de riesgo, transacciones) ---
{internal_context}

--- Contexto externo (mercado en tiempo real, noticias) ---
{external_context}

--- Senal de analisis riesgo-mercado (unica fuente de verdad para las cifras \
de esta seccion; no reutilizar numeros del contexto de arriba para estos campos) ---
senal_categoria_riesgo: {risk_category}
senal_tolerancia_drawdown_pct: {risk_tolerance}
senal_volatilidad_7d_pct: {volatility}
senal_cambio_7d_pct: {change}
senal_tendencia: {trend}
senal_sentimiento: {sentiment}
senal_excede_tolerancia_riesgo: {exceeds_tolerance}

Instrucciones de salida:
1. Indica una recomendacion clara: comprar, vender o mantener.
2. Justifica la recomendacion en lenguaje natural citando al menos un dato \
numerico concreto de la seccion "Senal de analisis riesgo-mercado" (ej. \
senal_volatilidad_7d_pct, senal_cambio_7d_pct, senal_tolerancia_drawdown_pct).
3. Si senal_excede_tolerancia_riesgo es verdadero, la recomendacion debe \
priorizar la preservacion de capital sobre el retorno.
"""


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(sin resultados relevantes)"
    return "\n".join(f"- {c.text}" for c in chunks)


class GeneratorAgent:
    def __init__(self, llm: BaseLLM):
        self._llm = llm

    def build_prompt(
        self,
        ticker: str,
        internal_chunks: list[RetrievedChunk],
        external_chunks: list[RetrievedChunk],
        signal: RiskMarketSignal,
    ) -> str:
        return PROMPT_TEMPLATE.format(
            ticker=ticker,
            internal_context=_format_chunks(internal_chunks),
            external_context=_format_chunks(external_chunks),
            risk_category=signal.risk_category,
            risk_tolerance=signal.risk_tolerance_drawdown_pct,
            volatility=signal.market_volatility_7d_pct,
            change=signal.market_change_7d_pct,
            trend=signal.market_trend,
            sentiment=signal.news_sentiment,
            exceeds_tolerance=signal.exceeds_risk_tolerance,
        )

    def run(
        self,
        ticker: str,
        internal_chunks: list[RetrievedChunk],
        external_chunks: list[RetrievedChunk],
        signal: RiskMarketSignal,
    ) -> str:
        prompt = self.build_prompt(ticker, internal_chunks, external_chunks, signal)
        return self._llm.generate(prompt)
