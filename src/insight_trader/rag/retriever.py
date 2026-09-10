"""Retriever RAG de doble fuente (interna/externa).

Construye dos indices separados -uno para datos internos de la fintech
(portafolio, perfil de riesgo, historial de transacciones) y otro para
datos externos de mercado (feeds de precios estilo Chainlink y noticias
financieras)- para que el agente de recuperacion pueda consultar cada
fuente de forma independiente y el agente de analisis pueda cruzarlas.

Usa FAISS (via LangChain) cuando la dependencia esta disponible; si no,
recurre automaticamente al VectorStore propio (misma interfaz logica),
para que el pipeline funcione en cualquier entorno sin bloquear la
evaluacion por una dependencia binaria (FAISS requiere wheels nativos).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from insight_trader import config
from insight_trader.rag.vector_store import VectorStore, cosine_similarity, embed_text

try:
    from langchain_community.vectorstores import FAISS
    from langchain_core.documents import Document as LCDocument

    from insight_trader.rag.embeddings import DeterministicEmbeddings

    _FAISS_AVAILABLE = True
except ImportError:  # pragma: no cover - depende del entorno de instalacion
    _FAISS_AVAILABLE = False


@dataclass
class RetrievedChunk:
    source: str  # "internal" | "external"
    text: str
    metadata: dict


@dataclass
class _RawDoc:
    doc_id: str
    text: str
    metadata: dict = field(default_factory=dict)


class _FaissIndex:
    """Adaptador delgado sobre langchain FAISS con la misma interfaz que
    `VectorStore.add` / `VectorStore.search`, para que `RAGRetriever` no
    necesite conocer cual de los dos backends esta activo."""

    def __init__(self):
        self._embeddings = DeterministicEmbeddings()
        self._store: FAISS | None = None
        self._pending: list[LCDocument] = []

    def add(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        self._pending.append(LCDocument(page_content=text, metadata={"doc_id": doc_id, **(metadata or {})}))

    def _ensure_built(self) -> None:
        if self._store is None and self._pending:
            self._store = FAISS.from_documents(self._pending, self._embeddings)

    def search(self, query: str, top_k: int = 3):
        self._ensure_built()
        if self._store is None:
            return []
        results = self._store.similarity_search(query, k=top_k)
        return [
            type("Doc", (), {"text": r.page_content, "metadata": r.metadata, "doc_id": r.metadata.get("doc_id")})()
            for r in results
        ]


def _new_index():
    return _FaissIndex() if _FAISS_AVAILABLE else VectorStore()


class RAGRetriever:
    """Orquesta la ingesta y recuperacion de las fuentes internas y externas."""

    def __init__(self):
        self.internal_index = _new_index()
        self.external_index = _new_index()
        self._internal_docs: list[_RawDoc] = []
        self._external_docs: list[_RawDoc] = []
        self._load_internal_sources()
        self._load_external_sources()

    def _add_internal(self, doc_id: str, text: str, metadata: dict) -> None:
        self.internal_index.add(doc_id, text, metadata)
        self._internal_docs.append(_RawDoc(doc_id, text, metadata))

    def _add_external(self, doc_id: str, text: str, metadata: dict) -> None:
        self.external_index.add(doc_id, text, metadata)
        self._external_docs.append(_RawDoc(doc_id, text, metadata))

    def _load_internal_sources(self) -> None:
        portfolio = json.loads(config.PORTFOLIO_PATH.read_text(encoding="utf-8"))
        transactions = json.loads(config.TRANSACTIONS_PATH.read_text(encoding="utf-8"))

        risk = portfolio["risk_profile"]
        self._add_internal(
            "risk_profile",
            (
                f"Perfil de riesgo del cliente {portfolio['client_name']}: categoria {risk['category']}, "
                f"tolerancia_drawdown_pct: {risk['max_drawdown_tolerance_pct']}, "
                f"horizonte de inversion {risk['investment_horizon_years']} anios. {risk['notes']}"
            ),
            {"type": "risk_profile", "client_id": portfolio["client_id"]},
        )

        for holding in portfolio["holdings"]:
            self._add_internal(
                f"holding_{holding['ticker']}",
                (
                    f"Posicion del cliente en {holding['ticker']} ({holding['name']}): "
                    f"{holding['quantity']} unidades, precio promedio de compra {holding['avg_buy_price']}, "
                    f"peso actual en portafolio {holding['current_weight_pct']}%, "
                    f"clase de activo {holding['asset_class']}."
                ),
                {"type": "holding", "ticker": holding["ticker"]},
            )

        for i, tx in enumerate(transactions):
            self._add_internal(
                f"tx_{i}",
                (
                    f"Transaccion historica: el {tx['date']} el cliente realizo {tx['action']} de "
                    f"{tx['quantity']} unidades de {tx['ticker']} a precio {tx['price']}."
                ),
                {"type": "transaction", "ticker": tx["ticker"]},
            )

    def _load_external_sources(self) -> None:
        market = json.loads(config.MARKET_DATA_PATH.read_text(encoding="utf-8"))
        news = json.loads(config.NEWS_PATH.read_text(encoding="utf-8"))

        for asset in market["assets"]:
            self._add_external(
                f"market_{asset['ticker']}",
                (
                    f"Datos de mercado en tiempo real ({market['source']}) para {asset['ticker']}: "
                    f"precio {asset['price']}, cambio_7d_pct: {asset['change_7d_pct']}, "
                    f"volatilidad_7d_pct: {asset['volatility_7d_pct']}, tendencia {asset['trend']}."
                ),
                {"type": "market_data", "ticker": asset["ticker"]},
            )

        for item in news:
            self._add_external(
                item["id"],
                (
                    f"Noticia sobre {item['ticker']} ({item['date']}): {item['headline']}. "
                    f"sentimiento: {item['sentiment']}. {item['summary']}"
                ),
                {"type": "news", "ticker": item["ticker"]},
            )

    @staticmethod
    def _filter_and_rank(docs: list[_RawDoc], query: str, ticker: str | None, top_k: int) -> list[_RawDoc]:
        """Recuperacion hibrida: primero acota por metadata (ticker exacto o
        documentos generales sin ticker, ej. el perfil de riesgo), luego
        ordena ese subconjunto por similitud semantica con la pregunta.

        El filtro por metadata evita que el embedding (deliberadamente
        liviano, ver `vector_store.embed_text`) confunda activos distintos
        que comparten casi todo su vocabulario (ej. dos filas de "Datos de
        mercado en tiempo real..."); el ranking semantico decide el orden
        dentro de ese subconjunto ya acotado."""
        candidates = [d for d in docs if ticker is None or d.metadata.get("ticker") in (None, ticker)]
        query_embedding = embed_text(query)
        scored = [(cosine_similarity(query_embedding, embed_text(d.text)), d) for d in candidates]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [d for _, d in scored[:top_k]]

    def retrieve_internal(
        self, query: str, ticker: str | None = None, top_k: int = config.TOP_K_RETRIEVAL
    ) -> list[RetrievedChunk]:
        if ticker is None:
            docs = self.internal_index.search(query, top_k)
        else:
            docs = self._filter_and_rank(self._internal_docs, query, ticker, top_k)
        return [RetrievedChunk("internal", d.text, d.metadata) for d in docs]

    def retrieve_external(
        self, query: str, ticker: str | None = None, top_k: int = config.TOP_K_RETRIEVAL
    ) -> list[RetrievedChunk]:
        if ticker is None:
            docs = self.external_index.search(query, top_k)
        else:
            docs = self._filter_and_rank(self._external_docs, query, ticker, top_k)
        return [RetrievedChunk("external", d.text, d.metadata) for d in docs]

    def retrieve_all(
        self, query: str, ticker: str | None = None, top_k: int = config.TOP_K_RETRIEVAL
    ) -> list[RetrievedChunk]:
        return self.retrieve_internal(query, ticker, top_k) + self.retrieve_external(query, ticker, top_k)
