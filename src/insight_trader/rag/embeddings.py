"""Embeddings deterministas compatibles con la interfaz de LangChain.

Se usa un embedding por hashing (ver `vector_store.embed_text`) en lugar de
un modelo neuronal (ej. sentence-transformers/OpenAI) para que el pipeline
sea 100% offline, gratuito y reproducible en la evaluacion. La interfaz
`Embeddings` de LangChain se respeta para que el resto del codigo (FAISS)
sea agnostico al proveedor: en produccion basta con reemplazar esta clase
por `OpenAIEmbeddings` o `HuggingFaceEmbeddings` sin tocar `retriever.py`.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings

from insight_trader.rag.vector_store import embed_text


class DeterministicEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return embed_text(text)
