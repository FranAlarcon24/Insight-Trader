"""Configuracion central del proyecto Insight Trader.

Los valores se leen de variables de entorno. Si existe un archivo `.env` en
la raiz del proyecto (fuera de git, ver `.env.example`) se carga primero;
las variables ya definidas en el entorno tienen prioridad sobre el archivo.
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    """Lector minimo de .env (CLAVE=valor), sin dependencias externas."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(__file__).parent / "data"

CLIENTS_DIR = DATA_DIR / "clients"
MARKET_DATA_PATH = DATA_DIR / "market_data.json"
NEWS_PATH = DATA_DIR / "news.json"
EVAL_CASES_PATH = DATA_DIR / "eval" / "casos.json"

DEFAULT_CLIENT_ID = "constanza_fuentes"

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


# ---------------------------------------------------------------- LLM
# Cadena de proveedores, en orden de preferencia. Si uno falla (clave
# invalida, 429, timeout, servicio caido) el agente pasa al siguiente:
#   nvidia     API de NVIDIA (build.nvidia.com), compatible con OpenAI
#   nvidia_alt segundo modelo de NVIDIA (misma clave), si el principal se cae
#   ollama    modelo abierto local servido por Ollama (respaldo privado)
#   mock      planificador determinista sin LLM (modo degradado)
#   anthropic Claude via API (opcional)
LLM_CHAIN = [p.strip() for p in os.getenv("INSIGHT_TRADER_LLM_CHAIN", "nvidia,nvidia_alt,ollama,mock").split(",") if p.strip()]
# Compatibilidad EP2: INSIGHT_TRADER_LLM_PROVIDER fija un unico proveedor
if os.getenv("INSIGHT_TRADER_LLM_PROVIDER"):
    LLM_CHAIN = [os.environ["INSIGHT_TRADER_LLM_PROVIDER"]]

# Pipeline RAG de la EP1 (src/insight_trader/llm.py): "mock" o "anthropic"
EP1_LLM_PROVIDER = os.getenv("INSIGHT_TRADER_EP1_LLM", "mock")

NVIDIA_BASE_URL =os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b")
# Modelos de razonamiento: "off" desactiva el modo thinking (mas rapido y
# con menos tokens; el plan ya viene dado por el planificador)
NVIDIA_THINKING = os.getenv("NVIDIA_THINKING", "off").lower() not in ("off", "0", "false")
NVIDIA_TIMEOUT_S = float(os.getenv("NVIDIA_TIMEOUT", "20"))
# Segundo modelo de NVIDIA (misma clave): respaldo si el principal se cae
NVIDIA_FALLBACK_MODEL = os.getenv("NVIDIA_FALLBACK_MODEL", "nvidia/nemotron-3.5-bolt-e4b")
NVIDIA_MAX_RETRIES = int(os.getenv("NVIDIA_MAX_RETRIES", "5"))
NVIDIA_BACKOFF_MAX_S = float(os.getenv("NVIDIA_BACKOFF_MAX", "30"))
# Limitador de tasa del lado del cliente (token bucket). La capa gratuita
# acepta ~40 solicitudes/min; 35 deja margen. 0 lo desactiva.
NVIDIA_RPM = float(os.getenv("NVIDIA_RPM", "20"))

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_CHAT_MODEL = os.getenv("INSIGHT_TRADER_OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT_S = float(os.getenv("INSIGHT_TRADER_OLLAMA_TIMEOUT", "180"))

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

# Si un proveedor falla, queda "abierto" (no se reintenta) durante este
# tiempo: evita pagar el timeout en cada paso del mismo turno.
CIRCUIT_OPEN_S = float(os.getenv("INSIGHT_TRADER_CIRCUIT_OPEN", "60"))
# Ante 429 la cuota se recupera en segundos: circuito corto + limitador adaptativo
CIRCUIT_OPEN_RATE_LIMIT_S = float(os.getenv("INSIGHT_TRADER_CIRCUIT_OPEN_429", "15"))

# ---------------------------------------------------------------- embeddings
# RAG + memoria: "ollama" (embeddinggemma, por defecto) o "hash"
EMBEDDING_PROVIDER = os.getenv("INSIGHT_TRADER_EMBEDDINGS", "ollama")
OLLAMA_EMBED_MODEL = os.getenv("INSIGHT_TRADER_EMBED_MODEL", "embeddinggemma:300m")
EMBEDDING_DIM = 128  # dimension del embedding por hashing (respaldo)
TOP_K_RETRIEVAL = 3

# ---------------------------------------------------------------- agente
MEMORY_DB_PATH = Path(os.getenv("INSIGHT_TRADER_MEMORY_DB", OUTPUT_DIR / "memoria_largo_plazo.db"))
# Memoria de corto plazo persistente (checkpointer SQLite de LangGraph)
CHECKPOINT_DB_NAME = "memoria_corto_plazo.db"
# Ventana de memoria de corto plazo: mensajes recientes que ve el LLM por turno
SHORT_TERM_WINDOW = 12
# Limite de pasos del ciclo agente -> herramientas por turno (evita bucles)
MAX_AGENT_STEPS = 25
# Guardrail de salida: corrige respuestas del LLM que violan reglas duras
GUARDRAIL_ENABLED = os.getenv("INSIGHT_TRADER_GUARDRAIL", "on").lower() not in ("off", "0", "false")
# Mejoras derivadas del analisis de registros (EP3, IE6/IE7). Se pueden
# apagar (INSIGHT_TRADER_MEJORAS=off) para reproducir la medicion "antes":
#   - alias: resolver nombres a tickers ("Tesla" -> TSLA, "bonos" -> BND)
#   - persistencia asincrona: el embedding del recuerdo sale del camino critico
#   - prompt con contador de tareas pendientes (menos respuestas prematuras)
IMPROVEMENTS_ENABLED = os.getenv("INSIGHT_TRADER_MEJORAS", "on").lower() not in ("off", "0", "false")

# ---------------------------------------------------------------- observabilidad (EP3)
OBSERVABILITY_DIR = Path(os.getenv("INSIGHT_TRADER_OBS_DIR", OUTPUT_DIR / "observabilidad"))
# Sal para seudonimizar ids de cliente en trazas y logs
PSEUDONYM_SALT = os.getenv("INSIGHT_TRADER_PSEUDONYM_SALT", "insight-trader-ep3")
