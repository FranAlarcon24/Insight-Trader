"""Agente orquestador: coordina recuperacion -> analisis -> generacion
para responder la pregunta de un cliente sobre un activo especifico."""
from __future__ import annotations

from dataclasses import dataclass

from insight_trader import config
from insight_trader.agents.analysis_agent import AnalysisAgent, RiskMarketSignal
from insight_trader.agents.generator_agent import GeneratorAgent
from insight_trader.agents.retrieval_agent import RetrievalAgent
from insight_trader.llm import BaseLLM, get_llm
from insight_trader.rag.retriever import RAGRetriever, RetrievedChunk


@dataclass
class CopilotResponse:
    ticker: str
    question: str
    signal: RiskMarketSignal
    internal_chunks: list[RetrievedChunk]
    external_chunks: list[RetrievedChunk]
    recommendation: str


class TradingCopilotOrchestrator:
    """Punto de entrada unico del pipeline de agentes (patron orquestador)."""

    def __init__(
        self,
        llm: BaseLLM | None = None,
        retriever: RAGRetriever | None = None,
        client_id: str = config.DEFAULT_CLIENT_ID,
    ):
        retriever = retriever or RAGRetriever(client_id)
        self._retrieval_agent = RetrievalAgent(retriever)
        self._analysis_agent = AnalysisAgent(client_id)
        self._generator_agent = GeneratorAgent(llm or get_llm())

    def ask(self, ticker: str, question: str) -> CopilotResponse:
        retrieved = self._retrieval_agent.run(ticker, question)
        signal = self._analysis_agent.run(ticker)
        recommendation = self._generator_agent.run(
            ticker, retrieved["internal"], retrieved["external"], signal
        )
        return CopilotResponse(
            ticker=ticker,
            question=question,
            signal=signal,
            internal_chunks=retrieved["internal"],
            external_chunks=retrieved["external"],
            recommendation=recommendation,
        )
