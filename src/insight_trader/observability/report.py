"""Datos del dashboard de observabilidad (EP3, IE4).

`dashboard_payload` arma, a partir de las trazas, lo que muestra la pagina
"Observabilidad" de la web: metricas por configuracion, hallazgos del
analisis automatico, la lista de turnos recientes y el detalle (spans) de
un subconjunto representativo. La usan la API en vivo (`/api/observability`)
y la exportacion estatica para Vercel (`scripts/exportar_observabilidad.py`).
"""
from __future__ import annotations

from datetime import datetime, timezone

from insight_trader import config
from insight_trader.observability.analysis import analyze

_SUMMARY_KEYS = ("trace_id", "ts", "cliente", "perfil", "escenario", "pregunta", "ticker", "accion", "estado",
                 "proveedor", "modelo", "degradado", "latencia_ms", "llm_ms", "herramientas_ms", "llm_llamadas",
                 "tokens_entrada", "tokens_salida", "pasos", "alertas", "replanificaciones", "eventos")


def _label(record: dict) -> str:
    return (record.get("eval") or {}).get("etiqueta") or "trafico_real"


def summarize(record: dict) -> dict:
    out = {k: record.get(k) for k in _SUMMARY_KEYS}
    ev = record.get("eval") or {}
    out.update({
        "configuracion": _label(record),
        "caso": ev.get("caso"),
        "categoria": ev.get("categoria"),
        "esperado": ev.get("esperado") if ev.get("final") else None,
        "correcto": (record["accion"] == ev["esperado"]) if ev.get("final") else None,
        "guardrail": (record.get("guardrail") or {}).get("intervino", False),
        "violaciones": (record.get("guardrail") or {}).get("violaciones", []),
        "cpu_pct": (record.get("recursos") or {}).get("cpu_pct_prom"),
        "rss_mb": (record.get("recursos") or {}).get("rss_mb_pico"),
    })
    return out


def _representative(records: list[dict], limit: int) -> list[dict]:
    """Turnos con detalle completo: los mas lentos, los degradados, los
    corregidos por el guardrail, los bloqueados, los errores y una muestra
    normal de cada configuracion."""
    picked: dict[str, dict] = {}

    def add(items):
        for r in items:
            if len(picked) < limit:
                picked.setdefault(r["trace_id"], r)

    by_label: dict[str, list[dict]] = {}
    for r in records:
        by_label.setdefault(_label(r), []).append(r)
    for rs in by_label.values():
        add(sorted(rs, key=lambda r: -r["latencia_ms"])[:2])
        add([r for r in rs if r["estado"] == "error"][:2])
        add([r for r in rs if (r.get("guardrail") or {}).get("intervino")][:2])
        add([r for r in rs if r.get("degradado")][:2])
        add([r for r in rs if r["estado"] == "bloqueado"][:1])
        add([r for r in rs if r.get("eventos")][:2])
        add(sorted(rs, key=lambda r: r["latencia_ms"])[len(rs) // 2: len(rs) // 2 + 1])
    return [{**summarize(r), "spans": r.get("spans", []), "llm_detalle": r.get("llm_detalle", []),
             "nodos_ms": r.get("nodos_ms", {}), "herramientas": r.get("herramientas", []),
             "respuesta": r.get("respuesta"), "seguridad": r.get("seguridad"),
             "guardrail_detalle": r.get("guardrail"), "recursos": r.get("recursos")}
            for r in picked.values()]


def dashboard_payload(records: list[dict], recent: int = 300, detailed: int = 40) -> dict:
    report = analyze(records)
    ordered = sorted(records, key=lambda r: r["ts"], reverse=True)
    return {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_turnos": len(records),
        "configuraciones": report["metricas"],
        "hallazgos": report["hallazgos"],
        "turnos": [summarize(r) for r in ordered[:recent]],
        "detalle": _representative(ordered, detailed),
        "ajustes": {
            "cadena_llm": config.LLM_CHAIN,
            "modelo_nvidia": config.NVIDIA_MODEL,
            "modelo_ollama": config.OLLAMA_CHAT_MODEL,
            "embeddings": f"{config.EMBEDDING_PROVIDER}:{config.OLLAMA_EMBED_MODEL}",
            "guardrail": config.GUARDRAIL_ENABLED,
        },
    }
