"""Agente de recuperacion: consulta ambas fuentes (interna/externa) segun
la pregunta del cliente."""
from __future__ import annotations

from insight_trader.rag.retriever import RAGRetriever, RetrievedChunk


class RetrievalAgent:
    def __init__(self, retriever: RAGRetriever):
        self._retriever = retriever

    def run(self, ticker: str, question: str) -> dict[str, list[RetrievedChunk]]:
        internal_query = f"{ticker} {question} perfil de riesgo posicion transacciones"
        external_query = f"{ticker} {question} precio volatilidad tendencia noticias"
        return {
            "internal": self._retriever.retrieve_internal(internal_query, ticker=ticker),
            "external": self._retriever.retrieve_external(external_query, ticker=ticker),
        }
