"""Metricas de observabilidad calculadas desde las trazas (EP3, IE1/IE2).

| Metrica                    | Definicion                                                          |
|----------------------------|---------------------------------------------------------------------|
| precision                  | turnos finales evaluados con accion == esperada / turnos evaluados  |
| precision_llm_sin_guardrail| igual, pero con la accion que redacto el LLM antes del guardrail    |
| consistencia               | por caso, % de repeticiones que coinciden con la accion mas comun;  |
|                            | se promedia entre casos (1.0 = siempre responde lo mismo)          |
| consistencia_herramientas  | igual, sobre la secuencia de herramientas ejecutadas                |
| tasa_error                 | turnos con excepcion / turnos                                       |
| tasa_degradado             | turnos respondidos por un proveedor de respaldo / turnos            |
| tasa_guardrail             | turnos en que el guardrail corrigio la respuesta / turnos           |
| tasa_violacion_llm         | turnos en que el LLM violo una regla dura (corregida o no) / turnos |
| eventos                    | conteo por tipo: 429, timeout, respuesta prematura, etc.            |
| latencia p50/p95/p99       | del turno completo, por nodo, por herramienta y del LLM             |
| tokens, llamadas al LLM    | promedio por turno                                                  |
| recursos                   | CPU (% de un nucleo) y memoria RSS pico del proceso del agente      |
"""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean


def percentile(values: list[float], p: float) -> float:
    """Percentil con interpolacion lineal (mismo criterio que numpy)."""
    if not values:
        return 0.0
    data = sorted(values)
    k = (len(data) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(data) - 1)
    return round(data[lo] + (data[hi] - data[lo]) * (k - lo), 1)


def latency_stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "p50": 0, "p95": 0, "p99": 0, "prom": 0, "max": 0}
    return {"n": len(values), "p50": percentile(values, 50), "p95": percentile(values, 95),
            "p99": percentile(values, 99), "prom": round(mean(values), 1), "max": round(max(values), 1)}


def _rate(part: int, total: int) -> float:
    return round(part / total, 4) if total else 0.0


def _modal_share(values: list) -> float:
    if not values:
        return 0.0
    return Counter(values).most_common(1)[0][1] / len(values)


def group_metrics(records: list[dict]) -> dict:
    """Metricas de un conjunto de trazas (una configuracion)."""
    n = len(records)
    evaluated = [r for r in records if (r.get("eval") or {}).get("final")]

    # ------------------------------------------------ precision
    correct = [r for r in evaluated if r["accion"] == r["eval"]["esperado"]]
    raw_correct = [r for r in evaluated
                   if ((r.get("guardrail") or {}).get("accion_llm") or r["accion"]) == r["eval"]["esperado"]
                   or r["accion"] == "bloqueado" == r["eval"]["esperado"]]
    by_category: dict[str, list[bool]] = defaultdict(list)
    by_scenario: dict[str, list[bool]] = defaultdict(list)
    for r in evaluated:
        ok = r["accion"] == r["eval"]["esperado"]
        by_category[r["eval"]["categoria"]].append(ok)
        by_scenario[r["escenario"]].append(ok)

    # ------------------------------------------------ consistencia
    per_case_actions: dict[str, list[str]] = defaultdict(list)
    per_case_tools: dict[str, list[tuple]] = defaultdict(list)
    for r in evaluated:
        per_case_actions[r["eval"]["caso"]].append(r["accion"])
        per_case_tools[r["eval"]["caso"]].append(tuple(h["nombre"] for h in r.get("herramientas", [])))
    repeated = {c: a for c, a in per_case_actions.items() if len(a) > 1}
    inconsistent = sorted(c for c, a in repeated.items() if len(set(a)) > 1)

    # ------------------------------------------------ errores y eventos
    events = Counter(e["tipo"] for r in records for e in r.get("eventos", []))
    # Turnos afectados por cada tipo (un turno puede tener varios eventos iguales)
    event_turns = Counter(t for r in records for t in {e["tipo"] for e in r.get("eventos", [])})
    violation_turns = Counter(v for r in records for v in set((r.get("guardrail") or {}).get("violaciones", [])))
    violations = Counter(v for r in records for v in (r.get("guardrail") or {}).get("violaciones", []))
    tool_errors = Counter(h["nombre"] for r in records for h in r.get("herramientas", []) if h["estado"] == "error")

    # ------------------------------------------------ latencia
    node_lat: dict[str, list[float]] = defaultdict(list)
    tool_lat: dict[str, list[float]] = defaultdict(list)
    llm_call_lat: list[float] = []
    for r in records:
        for node, ms in (r.get("nodos_ms") or {}).items():
            node_lat[node].append(ms)
        for h in r.get("herramientas", []):
            tool_lat[h["nombre"]].append(h["ms"])
        for c in r.get("llm_detalle", []):
            if c.get("proveedor"):
                llm_call_lat.append(c.get("ms", 0))
    totals = [r["latencia_ms"] for r in records]

    providers = Counter(r.get("proveedor") or "ninguno" for r in records)
    return {
        "turnos": n,
        "turnos_evaluados": len(evaluated),
        "precision": _rate(len(correct), len(evaluated)),
        "precision_llm_sin_guardrail": _rate(len(raw_correct), len(evaluated)),
        "precision_por_categoria": {k: _rate(sum(v), len(v)) for k, v in sorted(by_category.items())},
        "precision_por_escenario": {k: _rate(sum(v), len(v)) for k, v in sorted(by_scenario.items())},
        "fallos_de_precision": [
            {"caso": r["eval"]["caso"], "categoria": r["eval"]["categoria"], "esperado": r["eval"]["esperado"],
             "obtenido": r["accion"], "pregunta": r["pregunta"], "trace_id": r["trace_id"]}
            for r in evaluated if r["accion"] != r["eval"]["esperado"]
        ],
        "consistencia": round(mean(_modal_share(a) for a in repeated.values()), 4) if repeated else None,
        "consistencia_herramientas": round(mean(_modal_share(per_case_tools[c]) for c in repeated), 4)
        if repeated else None,
        "casos_inconsistentes": inconsistent,
        "tasa_error": _rate(sum(r["estado"] == "error" for r in records), n),
        "tasa_degradado": _rate(sum(bool(r.get("degradado")) for r in records), n),
        "tasa_bloqueo": _rate(sum(r["estado"] == "bloqueado" for r in records), n),
        "tasa_guardrail": _rate(sum(bool((r.get("guardrail") or {}).get("intervino")) for r in records), n),
        "tasa_violacion_llm": _rate(sum(bool((r.get("guardrail") or {}).get("violaciones")) for r in records), n),
        "tasa_turnos_con_evento": _rate(sum(bool(r.get("eventos")) for r in records), n),
        "eventos": dict(events.most_common()),
        "eventos_turnos": dict(event_turns),
        "violaciones": dict(violations.most_common()),
        "violaciones_turnos": dict(violation_turns),
        "errores_herramientas": dict(tool_errors),
        "proveedores": dict(providers),
        "latencia_turno_ms": latency_stats(totals),
        "latencia_llm_llamada_ms": latency_stats(llm_call_lat),
        "latencia_nodos_ms": {k: latency_stats(v) for k, v in sorted(node_lat.items())},
        "latencia_herramientas_ms": {k: latency_stats(v) for k, v in sorted(tool_lat.items())},
        "espera_cuota_ms": latency_stats([r.get("espera_cuota_ms", 0) for r in records]),
        "proporcion_llm":_rate(sum(r.get("llm_ms", 0) for r in records), sum(totals)) if totals else 0,
        "llm_llamadas_prom": round(mean(r.get("llm_llamadas", 0) for r in records), 2) if n else 0,
        "pasos_prom": round(mean(r.get("pasos", 0) for r in records), 2) if n else 0,
        "tokens_entrada_prom": round(mean(r.get("tokens_entrada", 0) for r in records), 1) if n else 0,
        "tokens_salida_prom": round(mean(r.get("tokens_salida", 0) for r in records), 1) if n else 0,
        "cpu_pct_prom": round(mean((r.get("recursos") or {}).get("cpu_pct_prom", 0) for r in records), 1) if n else 0,
        "cpu_s_prom": round(mean((r.get("recursos") or {}).get("cpu_s", 0) for r in records), 3) if n else 0,
        "rss_mb_pico": max(((r.get("recursos") or {}).get("rss_mb_pico", 0) for r in records), default=0),
    }


def compute_metrics(records: list[dict]) -> dict:
    """Metricas por configuracion evaluada (etiqueta) y para el trafico real
    (trazas sin etiqueta de evaluacion)."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        label = (r.get("eval") or {}).get("etiqueta") or "trafico_real"
        groups[label].append(r)
    return {label: group_metrics(rs) for label, rs in groups.items()}
