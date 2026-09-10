from insight_trader.rag.retriever import RAGRetriever


def test_retriever_loads_internal_and_external_sources():
    retriever = RAGRetriever()
    assert len(retriever.retrieve_internal("TSLA perfil de riesgo")) > 0
    assert len(retriever.retrieve_external("TSLA volatilidad noticias")) > 0


def test_internal_retrieval_is_relevant_to_queried_ticker():
    retriever = RAGRetriever()
    chunks = retriever.retrieve_internal("AAPL posicion transacciones", top_k=3)
    texts = " ".join(c.text for c in chunks)
    assert "AAPL" in texts


def test_external_retrieval_is_relevant_to_queried_ticker():
    retriever = RAGRetriever()
    chunks = retriever.retrieve_external("ETH volatilidad tendencia", top_k=3)
    texts = " ".join(c.text for c in chunks)
    assert "ETH" in texts
