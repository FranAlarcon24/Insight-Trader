"""Analisis automatico de registros (EP3, IE3/IE6).

Recorre las trazas y detecta patrones y anomalias:

- cuellos de botella: que nodo/herramienta concentra la latencia del turno;
- valores atipicos de latencia (regla de Tukey: > Q3 + 1.5 * IQR);
- arranque en frio: primeras ejecuciones mucho mas lentas que las siguientes;
- fallos de precision agrupados por categoria (patron de error repetido);
- inconsistencias: mismo caso, distinta accion entre repeticiones;
- eventos del LLM: 429, timeouts, respaldo, respuestas prematuras;
- intervenciones del guardrail y bloqueos de seguridad.

    python -m insight_trader.observability.analysis    # imprime el reporte en Markdown
"""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median

from insight_trader.observability.metrics import compute_metrics, percentile
from insight_trader.observability.store import TraceStore


def _tukey_outliers(records: list[dict]) -> list[dict]:
    values = [r["latencia_ms"] for r in records]
    if len(values) < 8:
        return []
    q1, q3 = percentile(values, 25), percentile(values, 75)
    limit = q3 + 1.5 * (q3 - q1)
    return [r for r in records if r["latencia_ms"] > limit]


def _dominant_span(record: dict) -> tuple[str, float]:
    """Nodo o herramienta (hoja) que mas tiempo consumio en el turno."""
    leaves = [s for s in record.get("spans", []) if s["tipo"] in ("herramienta", "llm")]
    leaves += [s for s in record.get("spans", []) if s["tipo"] == "nodo" and s["nombre"] not in ("herramientas", "agente")]
    if not leaves:
        return "-", 0.0
    top = max(leaves, key=lambda s: s["dur_ms"])
    return f"{top['tipo']}:{top['nombre']}", top["dur_ms"]


def analyze(records: list[dict]) -> dict:
    findings: list[dict] = []
    by_label: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_label[(r.get("eval") or {}).get("etiqueta") or "trafico_real"].append(r)

    for label, rs in by_label.items():
        if not rs:
            continue
        total = sum(r["latencia_ms"] for r in rs) or 1

        # --- cuello de botella: donde se va el tiempo (suma por nodo)
        node_share = Counter()
        for r in rs:
            for node, ms in (r.get("nodos_ms") or {}).items():
                node_share[node] += ms
        if node_share:
            node, ms = node_share.most_common(1)[0]
            findings.append({
                "configuracion": label, "tipo": "cuello_de_botella", "severidad": "alta" if ms / total > 0.5 else "media",
                "titulo": f"El nodo '{node}' concentra el {ms / total:.0%} del tiempo",
                "detalle": ", ".join(f"{k} {v / total:.0%}" for k, v in node_share.most_common(4)),
                "evidencia": {k: round(v / total, 3) for k, v in node_share.most_common()},
            })

        # --- hoja dominante por turno (que operacion concreta)
        dominant = Counter(_dominant_span(r)[0] for r in rs)
        name, count = dominant.most_common(1)[0]
        findings.append({
            "configuracion": label, "tipo": "operacion_dominante", "severidad": "media",
            "titulo": f"'{name}' es la operacion mas lenta en {count} de {len(rs)} turnos",
            "detalle": ", ".join(f"{k} ({v})" for k, v in dominant.most_common(4)),
        })

        # --- arranque en frio
        ordered = sorted(rs, key=lambda r: r["ts"])
        if len(ordered) >= 6:
            first = ordered[0]["latencia_ms"]
            rest = median(r["latencia_ms"] for r in ordered[1:])
            if rest and first > 3 * rest:
                findings.append({
                    "configuracion": label, "tipo": "arranque_en_frio", "severidad": "media",
                    "titulo": f"Primer turno {first / 1000:.1f} s vs mediana {rest / 1000:.1f} s ({first / rest:.0f}x)",
                    "detalle": f"Operacion dominante del primer turno: {_dominant_span(ordered[0])[0]}",
                    "trace_id": ordered[0]["trace_id"],
                })

        # --- atipicos de latencia
        outliers = _tukey_outliers(rs)
        if outliers:
            findings.append({
                "configuracion": label, "tipo": "latencia_atipica", "severidad": "media",
                "titulo": f"{len(outliers)} turnos con latencia atipica (regla de Tukey)",
                "detalle": "; ".join(f"{o['trace_id']} {o['latencia_ms'] / 1000:.1f} s ({_dominant_span(o)[0]})"
                                     for o in sorted(outliers, key=lambda o: -o["latencia_ms"])[:5]),
            })

        # --- fallos de precision repetidos por categoria
        misses = [r for r in rs if (r.get("eval") or {}).get("final") and r["accion"] != r["eval"]["esperado"]]
        by_cat = defaultdict(list)
        for r in misses:
            by_cat[r["eval"]["categoria"]].append(r)
        for cat, items in sorted(by_cat.items(), key=lambda kv: -len(kv[1])):
            got = Counter(i["accion"] for i in items).most_common(1)[0][0]
            findings.append({
                "configuracion": label, "tipo": "patron_de_error", "severidad": "alta",
                "titulo": f"{len(items)} errores de precision en '{cat}' (responde '{got}')",
                "detalle": " | ".join(sorted({f"{i['eval']['caso']}: {i['pregunta'][:70]}" for i in items})),
            })

        # --- inconsistencias entre repeticiones
        actions = defaultdict(set)
        for r in rs:
            if (r.get("eval") or {}).get("final"):
                actions[r["eval"]["caso"]].add(r["accion"])
        inconsistent = {c: sorted(a) for c, a in actions.items() if len(a) > 1}
        if inconsistent:
            findings.append({
                "configuracion": label, "tipo": "inconsistencia", "severidad": "alta",
                "titulo": f"{len(inconsistent)} casos con respuestas distintas entre repeticiones",
                "detalle": "; ".join(f"{c}: {', '.join(a)}" for c, a in sorted(inconsistent.items())),
            })

        # --- eventos del LLM y del plan
        events = Counter(e["tipo"] for r in rs for e in r.get("eventos", []))
        for kind, count in events.most_common():
            findings.append({
                "configuracion": label, "tipo": f"evento:{kind}",
                "severidad": "alta" if kind.startswith("llm_") or kind == "limite_de_pasos" else "media",
                "titulo": f"{count} eventos '{kind}' en {len(rs)} turnos",
                "detalle": next((e["detalle"] for r in rs for e in r.get("eventos", []) if e["tipo"] == kind), ""),
            })

        # --- guardrail
        violations = Counter(v for r in rs for v in (r.get("guardrail") or {}).get("violaciones", []))
        if violations:
            fixed = sum(bool((r.get("guardrail") or {}).get("intervino")) for r in rs)
            findings.append({
                "configuracion": label, "tipo": "guardrail", "severidad": "alta",
                "titulo": f"El LLM violo reglas duras en {sum(violations.values())} ocasiones; el guardrail corrigio {fixed}",
                "detalle": ", ".join(f"{k} ({v})" for k, v in violations.most_common()),
            })

        blocked = [r for r in rs if r["estado"] == "bloqueado"]
        if blocked:
            findings.append({
                "configuracion": label, "tipo": "seguridad", "severidad": "info",
                "titulo": f"{len(blocked)} intentos de prompt injection bloqueados antes del LLM",
                "detalle": ", ".join(sorted({p for r in blocked for p in r["seguridad"]["inyeccion"]})),
            })
        pii = Counter(k for r in rs for k in (r.get("seguridad") or {}).get("pii_entrada", []))
        if pii:
            findings.append({
                "configuracion": label, "tipo": "privacidad", "severidad": "info",
                "titulo": f"Datos personales detectados y enmascarados en {sum(1 for r in rs if r['seguridad']['pii_entrada'])} preguntas",
                "detalle": ", ".join(f"{k} ({v})" for k, v in pii.most_common()),
            })

    order = {"alta": 0, "media": 1, "info": 2}
    findings.sort(key=lambda f: (f["configuracion"], order.get(f["severidad"], 3)))
    return {"hallazgos": findings, "metricas": compute_metrics(records)}


def to_markdown(report: dict) -> str:
    lines = ["# Analisis automatico de registros del agente", ""]
    current = None
    for f in report["hallazgos"]:
        if f["configuracion"] != current:
            current = f["configuracion"]
            m = report["metricas"].get(current, {})
            lat = m.get("latencia_turno_ms", {})
            lines += ["", f"## Configuracion: {current}", "",
                      f"- Turnos: {m.get('turnos')} | precision: {m.get('precision', 0):.1%} | "
                      f"consistencia: {m.get('consistencia')} | latencia p50/p95: {lat.get('p50')}/{lat.get('p95')} ms",
                      ""]
        lines.append(f"- **[{f['severidad']}] {f['titulo']}**  \n  {f['detalle']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    print(to_markdown(analyze(TraceStore().load())))


if __name__ == "__main__":
    main()
