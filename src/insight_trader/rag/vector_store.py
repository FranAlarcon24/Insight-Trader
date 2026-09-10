"""Vector store minimalista en memoria (similitud coseno).

Se implementa sin dependencias externas de embeddings (FAISS/OpenAI) para
que el proyecto corra offline y sin costo. La interfaz (`add`, `search`)
es compatible con un reemplazo por FAISS + embeddings reales en produccion:
bastaria con sustituir `embed_text` por un modelo real y `VectorStore` por
`faiss.IndexFlatIP`.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

from insight_trader.config import EMBEDDING_DIM


def embed_text(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """Genera un embedding determinista via hashing de n-gramas de palabras.

    No captura semantica real (a diferencia de un embedding neuronal), pero
    es suficiente para demostrar el pipeline de recuperacion: documentos con
    vocabulario compartido (mismo ticker, mismos terminos financieros)
    obtienen mayor similitud coseno entre si.
    """
    vector = [0.0] * dim
    words = text.lower().split()
    for word in words:
        digest = hashlib.sha256(word.encode("utf-8")).hexdigest()
        index = int(digest, 16) % dim
        vector[index] += 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
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
