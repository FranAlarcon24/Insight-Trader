"""Banco de evaluacion del agente (EP3, IE1/IE2).

Ejecuta los casos de `data/eval/casos.json` N veces con una configuracion
(cadena de LLM, guardrail on/off) y etiqueta cada traza con el caso, la
categoria, la repeticion y la accion esperada. Las metricas se calculan
despues, solo a partir de las trazas (`metrics.py`), igual que se haria en
produccion con las trazas reales.

    python -m insight_trader.observability.evaluation --etiqueta mock --cadena mock --reps 1
    python -m insight_trader.observability.evaluation --etiqueta nvidia --cadena nvidia,mock --reps 3
    python -m insight_trader.observability.evaluation --etiqueta nvidia_sin_guardrail --cadena nvidia,mock --guardrail off
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from insight_trader import config
from insight_trader.agent.memory import LongTermMemory
from insight_trader.observability.store import TraceStore


def load_cases(path: Path | None = None, ids: list[str] | None = None, categories: list[str] | None = None) -> list[dict]:
    data = json.loads(Path(path or config.EVAL_CASES_PATH).read_text(encoding="utf-8"))
    cases = data["casos"]
    if ids:
        cases = [c for c in cases if c["id"] in ids]
    if categories:
        cases = [c for c in cases if c["categoria"] in categories]
    return cases


def run_case(case: dict, rep: int, label: str, chain: list[str], store: TraceStore, workdir: Path,
             retry_degraded: int = 0, wait_s: float = 60.0) -> dict:
    """Ejecuta un caso. Con `retry_degraded`, si el caso termina en modo
    degradado (el proveedor limito la cuota), el intento se marca como
    descartado, se espera `wait_s` y se repite: asi se mide el LLM y no el
    respaldo. Los descartes quedan registrados y se informan aparte."""
    for attempt in range(retry_degraded + 1):
        outcome = _run_case_once(case, rep, label, chain, store, workdir)
        if not outcome.pop("_degradado", False) or attempt == retry_degraded:
            outcome["descartes"] = attempt
            return outcome
        store.mark_discarded(set(outcome["_trazas"]), "cuota del proveedor (429): caso repetido")
        print(f"[{label}] rep {rep} {case['id']} degradado por cuota; se descarta y se repite en {wait_s:.0f} s",
              flush=True)
        time.sleep(wait_s)
    return outcome


def _run_case_once(case: dict, rep: int, label: str, chain: list[str], store: TraceStore, workdir: Path) -> dict:
    from insight_trader.agent.graph import InsightTraderAgent  # import diferido: respeta el guardrail del entorno

    agent = InsightTraderAgent(
        client_id=case["cliente"], scenario=case["escenario"],
        memory=LongTermMemory(":memory:"),  # cada repeticion parte sin recuerdos
        output_dir=workdir, chain=chain, trace_store=store,
    )
    # Hilo unico por intento: un reintento no hereda la memoria del descartado
    thread = f"eval-{label}-{case['id']}-{rep}-{uuid.uuid4().hex[:6]}"
    turns = case["turnos"]
    result = None
    traces: list[str] = []
    degraded = False
    for i, turn in enumerate(turns):
        if isinstance(turn, dict):
            if turn.get("escenario"):
                agent.set_scenario(turn["escenario"])
            question = turn["pregunta"]
        else:
            question = turn
        final = i == len(turns) - 1
        tags = {"etiqueta": label, "caso": case["id"], "categoria": case["categoria"], "rep": rep,
                "turno": i + 1, "final": final, "guardrail": config.GUARDRAIL_ENABLED}
        if final:
            tags["esperado"] = case["esperado"]
        try:
            result = agent.ask(question, thread_id=thread, tags=tags)
            traces.append(result.traza_id)
            degraded = degraded or result.degradado
        except Exception as exc:  # la traza de error ya quedo registrada
            return {"caso": case["id"], "rep": rep, "accion": "error", "esperado": case["esperado"],
                    "correcto": False, "error": str(exc)[:200]}
    correct = result.accion_categoria == case["esperado"]
    if case.get("debe_respetar_preferencia"):
        correct = correct and bool(result.findings.get("restricciones"))
    return {"caso": case["id"], "rep": rep, "accion": result.accion_categoria, "esperado": case["esperado"],
            "correcto": correct, "proveedor": result.proveedor, "ms": result.latencia_ms,
            "_degradado": degraded, "_trazas": traces}


def run_evaluation(label: str, chain: list[str], reps: int = 1, cases: list[dict] | None = None,
                   store: TraceStore | None = None, pause_s: float = 0.0, retry_degraded: int = 0,
                   wait_s: float = 60.0) -> list[dict]:
    store = store or TraceStore()
    cases = cases or load_cases()
    workdir = Path(tempfile.mkdtemp(prefix=f"eval_{label}_"))
    results = []
    try:
        for rep in range(1, reps + 1):
            for case in cases:
                outcome = run_case(case, rep, label, chain, store, workdir, retry_degraded, wait_s)
                results.append(outcome)
                mark = "ok " if outcome["correcto"] else "MAL"
                print(f"[{label}] rep {rep} {case['id']:<4} {case['categoria']:<22} {mark} "
                      f"esperado={outcome['esperado']:<17} obtenido={outcome['accion']:<17} "
                      f"{outcome.get('proveedor') or '-':<7} {outcome.get('ms', 0):>8.0f} ms", flush=True)
                if pause_s:
                    time.sleep(pause_s)  # respeta el limite de solicitudes por minuto del proveedor
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    total = len(results)
    ok = sum(r["correcto"] for r in results)
    print(f"[{label}] precision {ok}/{total} = {ok / total:.1%}" if total else "sin casos")
    discarded = sum(r.get("descartes", 0) for r in results)
    if discarded:
        print(f"[{label}] intentos descartados por cuota del proveedor: {discarded}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Banco de evaluacion del agente Insight Trader (EP3)")
    parser.add_argument("--etiqueta", required=True, help="Nombre de la configuracion (aparece en el dashboard)")
    parser.add_argument("--cadena", default=",".join(config.LLM_CHAIN), help="Proveedores en orden, ej. nvidia,mock")
    parser.add_argument("--reps", type=int, default=1, help="Repeticiones por caso (consistencia)")
    parser.add_argument("--casos", nargs="*", help="Ids de casos (por defecto todos)")
    parser.add_argument("--categorias", nargs="*", help="Categorias de casos")
    parser.add_argument("--guardrail", choices=("on", "off"), default=None)
    parser.add_argument("--pausa", type=float, default=0.0, help="Segundos entre casos (limite de la API)")
    parser.add_argument("--reintentar-degradados", type=int, default=0,
                        help="Repite (y descarta) un caso que termino en modo degradado por cuota")
    parser.add_argument("--espera", type=float, default=60.0, help="Segundos antes de repetir un caso degradado")
    args = parser.parse_args()
    if args.guardrail:
        os.environ["INSIGHT_TRADER_GUARDRAIL"] = args.guardrail
        config.GUARDRAIL_ENABLED = args.guardrail == "on"
    chain = [p.strip() for p in args.cadena.split(",") if p.strip()]
    run_evaluation(args.etiqueta, chain, args.reps, load_cases(ids=args.casos, categories=args.categorias),
                   pause_s=args.pausa, retry_degraded=args.reintentar_degradados, wait_s=args.espera)


if __name__ == "__main__":
    main()
