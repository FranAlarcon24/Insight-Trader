"""Embeddings y vector store minimalista en memoria (similitud coseno).

`embed_text` es el unico punto de entrada a los embeddings del proyecto: lo
usan el RAG (FAISS y este VectorStore) y la memoria de largo plazo. El
proveedor se elige con `INSIGHT_TRADER_EMBEDDINGS`:

- "ollama" (por defecto): modelo neuronal multilingue `embeddinggemma`
  servido por Ollama en local. Captura semantica real: "cripto" queda
  cerca de "Ethereum" aunque no compartan palabras.
- "hash": embedding determinista por hashing de palabras. No captura
  semantica, pero es instantaneo y no necesita servicios externos; se usa
  en las pruebas y como respaldo automatico si Ollama no responde.

Los vectores se cachean por texto: el RAG re-rankea los mismos documentos
en cada consulta y sin cache cada busqueda repetiria las llamadas a Ollama.
"""
from __future__ import annotations

import hashlib
import logging
import math
import threading
from dataclasses import dataclass, field

from insight_trader import config
from insight_trader.config import EMBEDDING_DIM

log = logging.getLogger("insight_trader.embeddings")

_cache: dict[tuple[str, str], list[float]] = {}
_lock = threading.Lock()
_ollama_failed = False


def hash_embed(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Embedding determinista via hashing de palabras (respaldo sin red).

    No captura semantica real: solo documentos con vocabulario compartido
    (mismo ticker, mismos terminos) obtienen mayor similitud coseno.
    """
    vector = [0.0] * dim
    words = text.lower().split()
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).hexdigest()
        index = int(digest, 16) % dim
        vector[index] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def active_provider() -> str:
    """Proveedor efectivo: el configurado, salvo que Ollama haya fallado."""
    if config.EMBEDDING_PROVIDER == "ollama" and not _ollama_failed:
        return "ollama"
    return "hash"


def _ollama_embed(texts: list[str]) -> list[list[float]]:
    import ollama  # dependencia de langchain-ollama

    client = ollama.Client(host=config.OLLAMA_HOST, timeout=60)
    response = client.embed(model=config.OLLAMA_EMBED_MODEL, input=texts)
    return [_normalize(list(v)) for v in response["embeddings"]]


def embed_many(texts: list[str]) -> list[list[float]]:
    """Embeddings de varios textos en una sola llamada al proveedor."""
    global _ollama_failed
    provider = active_provider()
    missing = [t for t in dict.fromkeys(texts) if (provider, t) not in _cache]
    if missing:
        if provider == "ollama":
            try:
                vectors = _ollama_embed(missing)
            except Exception as exc:  # Ollama apagado, modelo no descargado, timeout...
                _ollama_failed = True
                log.warning("embeddings_fallback", extra={"evento": "embeddings_fallback", "error": str(exc)})
                return embed_many(texts)
        else:
            vectors = [hash_embed(t) for t in missing]
        with _lock:
            _cache.update({(provider, t): v for t, v in zip(missing, vectors)})
    return [_cache[(provider, t)] for t in texts]


def embed_text(text: str) -> list[float]:
    return embed_many([text])[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Vectores ya normalizados: el producto punto es el coseno. Si las
    dimensiones no coinciden (recuerdo guardado con otro proveedor) no son
    comparables y la similitud es 0."""
    if len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


@dataclass
class Document:
    doc_id: str
    text: str
    metadata: dict = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)


class VectorStore:
    def __init__(self):
        self._documents: list[Document] = []

    def add(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        embedding = embed_text(text)
        self._documents.append(Document(doc_id, text, metadata or {}, embedding))

    def search(self, query: str, top_k: int = 3) -> list[Document]:
        if not self._documents:
            return []
        query_embedding = embed_text(query)
        scored = [
            (cosine_similarity(query_embedding, doc.embedding), doc)
            for doc in self._documents
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]

    def __len__(self) -> int:
        return len(self._documents)
