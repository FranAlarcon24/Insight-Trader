"""Trazabilidad del agente (EP3, IE2/IE3).

`TraceCollector` es un callback de LangChain: LangGraph le avisa cuando
empieza y termina cada nodo del grafo, cada herramienta y cada llamada al
LLM. Con eso arma una lista de spans (inicio relativo, duracion, estado,
padre) que permite reconstruir la ejecucion como una cascada, igual que
LangSmith o Langfuse, pero local y sin enviar datos a terceros.

`ResourceMonitor` muestrea CPU y memoria del proceso mientras dura el turno.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any

import psutil
from langchain_core.callbacks import BaseCallbackHandler

from insight_trader.observability.privacy import mask_pii


class TraceCollector(BaseCallbackHandler):
    """Recolecta spans de nodos, herramientas y llamadas al LLM."""

    raise_error = False  # un fallo del tracing nunca debe romper al agente

    def __init__(self) -> None:
        self.t0 = time.perf_counter()
        self.spans: list[dict] = []
        self._open: dict[uuid.UUID, dict] = {}

    # ------------------------------------------------------------ helpers
    def _now_ms(self) -> float:
        return round((time.perf_counter() - self.t0) * 1000, 1)

    def _start(self, run_id, parent_run_id, kind: str, name: str, **extra) -> None:
        self._open[run_id] = {
            "id": str(run_id)[:8],
            "padre": str(parent_run_id)[:8] if parent_run_id else None,
            "tipo": kind,
            "nombre": name,
            "inicio_ms": self._now_ms(),
            "estado": "ok",
            **extra,
        }

    def _end(self, run_id, error: BaseException | None = None, **extra) -> None:
        span = self._open.pop(run_id, None)
        if span is None:
            return
        span["dur_ms"] = round(self._now_ms() - span["inicio_ms"], 1)
        if error is not None:
            span["estado"] = "error"
            span["error"] = mask_pii(f"{type(error).__name__}: {error}")[:300]
        span.update(extra)
        self.spans.append(span)

    # ------------------------------------------------------------ nodos del grafo
    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, metadata=None, **kwargs) -> Any:
        node = (metadata or {}).get("langgraph_node")
        name = kwargs.get("name")
        # LangGraph emite eventos tambien para runnables internos; solo
        # interesa el span que representa al nodo completo.
        if node and name == node:
            self._start(run_id, parent_run_id, "nodo", node, paso=(metadata or {}).get("langgraph_step"))

    def on_chain_end(self, outputs, *, run_id, **kwargs) -> Any:
        self._end(run_id)

    def on_chain_error(self, error, *, run_id, **kwargs) -> Any:
        self._end(run_id, error)

    # ------------------------------------------------------------ herramientas
    def on_tool_start(self, serialized, input_str, *, run_id, parent_run_id=None, **kwargs) -> Any:
        name = kwargs.get("name") or (serialized or {}).get("name", "herramienta")
        self._start(run_id, parent_run_id, "herramienta", name)

    def on_tool_end(self, output, *, run_id, **kwargs) -> Any:
        content = getattr(output, "content", output)
        status = getattr(output, "status", "success")
        failed = status == "error" or (isinstance(content, str) and content.startswith('{"error"'))
        self._end(run_id, None, **({"estado": "error", "error": mask_pii(str(content))[:300]} if failed else {}))

    def on_tool_error(self, error, *, run_id, **kwargs) -> Any:
        self._end(run_id, error)

    # ------------------------------------------------------------ LLM
    def on_chat_model_start(self, serialized, messages, *, run_id, parent_run_id=None, **kwargs) -> Any:
        model = (kwargs.get("invocation_params") or {}).get("model") or (kwargs.get("metadata") or {}).get(
            "ls_model_name") or (serialized or {}).get("name", "llm")
        self._start(run_id, parent_run_id, "llm", str(model), mensajes=len(messages[0]) if messages else 0)

    def on_llm_end(self, response, *, run_id, **kwargs) -> Any:
        tokens_in = tokens_out = 0
        try:
            message = response.generations[0][0].message
            usage = getattr(message, "usage_metadata", None) or {}
            tokens_in, tokens_out = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        except (AttributeError, IndexError):
            pass
        self._end(run_id, None, tokens_entrada=tokens_in, tokens_salida=tokens_out)

    def on_llm_error(self, error, *, run_id, **kwargs) -> Any:
        self._end(run_id, error)

    # ------------------------------------------------------------ resumen
    def finish(self) -> list[dict]:
        # Spans que nunca cerraron (ej. excepcion no capturada)
        for run_id in list(self._open):
            self._end(run_id, RuntimeError("span sin cierre"))
        return sorted(self.spans, key=lambda s: s["inicio_ms"])


class ResourceMonitor:
    """Muestrea CPU y memoria (RSS) del proceso cada `interval` segundos."""

    def __init__(self, interval: float = 0.1):
        self.interval = interval
        self.process = psutil.Process()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.rss_peak = 0

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.rss_peak = max(self.rss_peak, self.process.memory_info().rss)
            except psutil.Error:
                pass
            self._stop.wait(self.interval)

    def __enter__(self) -> "ResourceMonitor":
        self.cpu_start = self.process.cpu_times()
        self.wall_start = time.perf_counter()
        self.rss_start = self.process.memory_info().rss
        self.rss_peak = self.rss_start
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        cpu_end = self.process.cpu_times()
        wall = max(time.perf_counter() - self.wall_start, 1e-6)
        cpu_s = (cpu_end.user - self.cpu_start.user) + (cpu_end.system - self.cpu_start.system)
        self.summary = {
            "cpu_s": round(cpu_s, 3),
            # % de un nucleo: >100 significa que uso mas de un nucleo
            "cpu_pct_prom": round(100 * cpu_s / wall, 1),
            "rss_mb_inicio": round(self.rss_start / 2**20, 1),
            "rss_mb_pico": round(self.rss_peak / 2**20, 1),
        }
