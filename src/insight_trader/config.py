"""Configuracion central del proyecto Insight Trader."""
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

PORTFOLIO_PATH = DATA_DIR / "portfolio.json"
TRANSACTIONS_PATH = DATA_DIR / "transactions.json"
MARKET_DATA_PATH = DATA_DIR / "market_data.json"
NEWS_PATH = DATA_DIR / "news.json"

# Proveedor de LLM: "mock" (por defecto, sin costo/API key) o "anthropic".
LLM_PROVIDER = os.getenv("INSIGHT_TRADER_LLM_PROVIDER", "mock")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

# Parametros del pipeline RAG
EMBEDDING_DIM = 128
TOP_K_RETRIEVAL = 3
