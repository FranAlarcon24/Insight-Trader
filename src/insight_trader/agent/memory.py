"""Memoria de largo plazo del agente (IE3/IE4).

Dos niveles de memoria conviven en el agente:

- Corto plazo (dentro de una conversacion): el estado del grafo LangGraph
  (mensajes, ticker activo, plan) se guarda por `thread_id` con un
  checkpointer. Permite preguntas de seguimiento ("y ahora?") sin repetir
  el activo. Ver `agent/graph.py`.
- Largo plazo (entre conversaciones y reinicios del proceso): esta clase.
  Persiste en SQLite las interacciones pasadas (pregunta + recomendacion) y
  las preferencias declaradas por cada cliente, y las recupera por
  similitud semantica con la consulta actual.

La recuperacion semantica reutiliza los embeddings del pipeline RAG
(`rag.vector_store.embed_text`), de modo que reemplazarlos por un modelo
neuronal mejora a la vez el RAG y la memoria sin tocar esta clase.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from insight_trader import config
from insight_trader.rag.vector_store import cosine_similarity, embed_text

KINDS = ("interaccion", "preferencia")

# Bonificacion de score cuando el recuerdo es del mismo activo consultado:
# prioriza el historial del ticker sobre recuerdos solo parecidos en texto.
TICKER_MATCH_BONUS = 0.3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    ticker TEXT,
    content TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    embedding TEXT NOT NULL
)
"""


@dataclass
class MemoryItem:
    id: int
    client_id: str
    kind: str
    ticker: str | None
    content: str
    metadata: dict
    created_at: str
    score: float = 0.0

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "tipo": self.kind,
            "ticker": self.ticker,
            "contenido": self.content,
            "metadata": self.metadata,
            "fecha": self.created_at,
            "score": round(self.score, 3),
        }


class LongTermMemory:
    def __init__(self, path: str | Path | None = None):
        # ":memory:" crea una base efimera (util en pruebas)
        path = path or config.MEMORY_DB_PATH
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.execute(_SCHEMA)
        self._conn.commit()
        self._lock = threading.Lock()
        # Un solo hilo de escritura en segundo plano (mejora EP3): el turno
        # responde sin esperar el embedding del recuerdo.
        self._writer = ThreadPoolExecutor(max_workers=1, thread_name_prefix="memoria")
        self._pending: list[Future] = []

    def remember(
        self,
        client_id: str,
        kind: str,
        content: str,
        ticker: str | None = None,
        metadata: dict | None = None,
        embed_from: str | None = None,
    ) -> int:
        """Guarda un recuerdo. `embed_from` permite calcular el embedding
        sobre un resumen corto en vez del contenido completo."""
        if kind not in KINDS:
            raise ValueError(f"Tipo de memoria invalido: {kind}")
        embedding = json.dumps(embed_text(embed_from or content))
        with self._lock:
            cursor = self._conn.execute(
                "INSERT INTO memories (client_id, kind, ticker, content, metadata, created_at, embedding) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    client_id,
                    kind,
                    ticker,
                    content,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    datetime.now().isoformat(timespec="seconds"),
                    embedding,
                ),
            )
            self._conn.commit()
            return cursor.lastrowid

    def remember_async(self, *args, **kwargs) -> Future:
        """Como `remember`, pero en segundo plano. Las lecturas esperan a
        que terminen las escrituras pendientes (consistencia lectura-escritura)."""
        future = self._writer.submit(self.remember, *args, **kwargs)
        self._pending.append(future)
        return future

    def flush(self) -> None:
        pending, self._pending = self._pending, []
        for future in pending:
            future.result()

    def _rows(self, client_id: str, kind: str | None = None) -> list[tuple]:
        self.flush()
        sql = "SELECT id, client_id, kind, ticker, content, metadata, created_at, embedding FROM memories WHERE client_id = ?"
        params: list = [client_id]
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        return self._conn.execute(sql + " ORDER BY id", params).fetchall()

    @staticmethod
    def _to_item(row: tuple, score: float = 0.0) -> MemoryItem:
        return MemoryItem(row[0], row[1], row[2], row[3], row[4], json.loads(row[5]), row[6], score)

    def search(
        self,
        client_id: str,
        query: str,
        ticker: str | None = None,
        kind: str | None = None,
        top_k: int = 3,
    ) -> list[MemoryItem]:
        """Recuperacion semantica: similitud coseno entre la consulta y cada
        recuerdo del cliente, con bonificacion si coincide el ticker."""
        query_embedding = embed_text(query)
        scored = []
        for row in self._rows(client_id, kind):
            stored = json.loads(row[7])
            if len(stored) != len(query_embedding):
                # Guardado con otro proveedor de embeddings: se recalcula
                stored = embed_text(row[4])
            score = cosine_similarity(query_embedding, stored)
            if ticker and row[3] == ticker:
                score += TICKER_MATCH_BONUS
            scored.append(self._to_item(row, score))
        scored.sort(key=lambda item: (item.score, item.id), reverse=True)
        return scored[:top_k]

    def latest(self, client_id: str, kind: str, ticker: str | None = None) -> MemoryItem | None:
        rows = [r for r in self._rows(client_id, kind) if ticker is None or r[3] == ticker]
        return self._to_item(rows[-1]) if rows else None

    def preferences(self, client_id: str) -> list[MemoryItem]:
        return [self._to_item(r) for r in self._rows(client_id, "preferencia")]

    def count(self, client_id: str) -> int:
        return len(self._rows(client_id))

    def clear(self, client_id: str | None = None) -> None:
        self.flush()
        if client_id:
            self._conn.execute("DELETE FROM memories WHERE client_id = ?", (client_id,))
        else:
            self._conn.execute("DELETE FROM memories")
        self._conn.commit()
