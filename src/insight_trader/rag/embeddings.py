"""Adaptador de los embeddings del proyecto a la interfaz de LangChain.

FAISS (via LangChain) espera un objeto `Embeddings`. Esta clase delega en
`vector_store.embed_many`, que usa el proveedor configurado (Ollama con
`embeddinggemma` por defecto, o hashing como respaldo). Asi el RAG y la
memoria de largo plazo comparten siempre el mismo espacio vectorial.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings

from insight_trader.rag.vector_store import embed_many, embed_text


class ProjectEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embed_many(texts)

    def embed_query(self, text: str) -> list[float]:
        return embed_text(text)


# Nombre anterior (EP1/EP2), se mantiene por compatibilidad
DeterministicEmbeddings = ProjectEmbeddings
