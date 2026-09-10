"""Configuracion central del proyecto Insight Trader."""
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

CLIENTS_DIR = DATA_DIR / "clients"
MARKET_DATA_PATH = DATA_DIR / "market_data.json"
NEWS_PATH = DATA_DIR / "news.json"

DEFAULT_CLIENT_ID = "constanza_fuentes"


def client_data_path(client_id: str) -> Path:
    return CLIENTS_DIR / f"{client_id}.json"


def list_client_ids() -> list[str]:
    return sorted(p.stem for p in CLIENTS_DIR.glob("*.json"))

# Proveedor de LLM: "mock" (por defecto, sin costo/API key) o "anthropic".
LLM_PROVIDER = os.getenv("INSIGHT_TRADER_LLM_PROVIDER", "mock")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

# Parametros del pipeline RAG
EMBEDDING_DIM = 128
TOP_K_RETRIEVAL = 3
