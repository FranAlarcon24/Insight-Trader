"""Exporta las trazas a los artefactos del EP3.

- web-react/src/data/observabilidad.json : datos del dashboard (modo
  estatico en Vercel, cuando la API local no esta disponible).
- docs/analisis_registros.md             : reporte del analisis automatico.

    python scripts/exportar_observabilidad.py
"""
from __future__ import annotations

import json
from pathlib import Path

from insight_trader.observability.analysis import analyze, to_markdown
from insight_trader.observability.report import dashboard_payload
from insight_trader.observability.store import TraceStore

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    records = TraceStore().load()
    if not records:
        raise SystemExit("No hay trazas en outputs/observabilidad/trazas.jsonl: corre primero la evaluacion.")
    payload = dashboard_payload(records)
    out = ROOT / "web-react" / "src" / "data" / "observabilidad.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    md = ROOT / "docs" / "analisis_registros.md"
    md.write_text(to_markdown(analyze(records)), encoding="utf-8")
    print(f"{len(records)} trazas -> {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB) y {md.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
