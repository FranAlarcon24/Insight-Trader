"""Configuracion central del proyecto Insight Trader."""
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

CLIENTS_DIR = DATA_DIR / "clients"
MARKET_DATA_PATH = DATA_DIR / "market_data.json"
NEWS_PATH = DATA_DIR / "news.json"

DEFAULT_CLIENT_ID = "constanza_fuentes"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(os.getenv("INSIGHT_TRADER_OUTPUT_DIR", PROJECT_ROOT / "outputs"))
# Clientes creados desde la interfaz web: fuera del paquete (y de git) para
# no mezclarlos con los 3 clientes simulados base.
CUSTOM_CLIENTS_DIR = OUTPUT_DIR / "clientes"


def client_data_path(client_id: str) -> Path:
    custom = CUSTOM_CLIENTS_DIR / f"{client_id}.json"
    return custom if custom.exists() else CLIENTS_DIR / f"{client_id}.json"


def is_custom_client(client_id: str) -> bool:
    return (CUSTOM_CLIENTS_DIR / f"{client_id}.json").exists()


def list_client_ids() -> list[str]:
    ids = {p.stem for p in CLIENTS_DIR.glob("*.json")}
    ids |= {p.stem for p in CUSTOM_CLIENTS_DIR.glob("*.json")}
    return sorted(ids)

# Proveedor de LLM: "mock" (por defecto, sin costo/API key) o "anthropic".
LLM_PROVIDER = os.getenv("INSIGHT_TRADER_LLM_PROVIDER", "mock")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

# Parametros del pipeline RAG
EMBEDDING_DIM = 128
TOP_K_RETRIEVAL = 3

# Parametros del agente (EP2)
MEMORY_DB_PATH = Path(os.getenv("INSIGHT_TRADER_MEMORY_DB", OUTPUT_DIR / "memoria_largo_plazo.db"))
# Ventana de memoria de corto plazo: mensajes recientes que ve el LLM por turno
SHORT_TERM_WINDOW = 12
# Limite de pasos del ciclo agente -> herramientas por turno (evita bucles)
MAX_AGENT_STEPS = 25
