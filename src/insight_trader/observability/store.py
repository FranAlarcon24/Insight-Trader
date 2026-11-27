"""Persistencia de trazas y logs estructurados (EP3, IE3).

- `trazas.jsonl`: una linea JSON por turno del agente, con sus spans,
  latencias, tokens, recursos, decisiones de re-planificacion, eventos de
  seguridad y de guardrail. Es la fuente del dashboard y del analisis.
- `agente.log`: log estructurado (JSON por linea) con niveles INFO/WARNING/
  ERROR, rotado a 5 MB. Lo que un operador revisaria en produccion.

Ninguno guarda datos personales en claro: las preguntas y respuestas pasan
por `mask_pii` y el cliente se identifica con un seudonimo.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from insight_trader import config

_write_lock = threading.Lock()
_logging_ready: set[Path] = set()

# Campos estandar de LogRecord: lo demas se considera contexto del evento
_STD = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "nivel": record.levelname,
            "logger": record.name,
            "mensaje": record.getMessage(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _STD})
        if record.exc_info:
            payload["excepcion"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(directory: Path | None = None) -> None:
    """Configura el logger `insight_trader` para escribir JSON en
    `<directory>/agente.log` (una sola vez por directorio)."""
    directory = Path(directory or config.OBSERVABILITY_DIR)
    if directory in _logging_ready:
        return
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(directory / "agente.log", maxBytes=5 * 2**20, backupCount=3, encoding="utf-8")
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("insight_trader")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    _logging_ready.add(directory)


class TraceStore:
    def __init__(self, directory: Path | None = None):
        self.directory = Path(directory or config.OBSERVABILITY_DIR)
        self.path = self.directory / "trazas.jsonl"

    def append(self, record: dict) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with _write_lock, self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def load(self, include_discarded: bool = False) -> list[dict]:
        """Trazas guardadas. Por defecto omite los intentos de evaluacion
        descartados (repetidos porque el proveedor limito la cuota)."""
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue  # linea truncada (corte durante escritura)
                if include_discarded or not (record.get("eval") or {}).get("descartado"):
                    records.append(record)
        return records

    def mark_discarded(self, trace_ids: set[str], reason: str) -> None:
        """Marca intentos de evaluacion como descartados (quedan en el
        archivo como evidencia, pero no cuentan en las metricas)."""
        with _write_lock:
            records = self.load(include_discarded=True)
            for r in records:
                if r.get("trace_id") in trace_ids:
                    r.setdefault("eval", {}).update({"descartado": True, "motivo_descarte": reason})
            self.path.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in records),
                                 encoding="utf-8")
