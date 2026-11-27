import { useEffect, useState } from "react";
import staticData from "../data/observabilidad.json";
import { fetchObservability } from "./api";
import { HBarChart, Waterfall } from "./charts";
import "./observability.css";

// Dashboard de observabilidad (EP3): metricas de precision, consistencia,
// errores, latencia y recursos del agente, calculadas desde sus trazas.
// Con la API local muestra datos en vivo; en Vercel, la ultima exportacion.

const CONFIG_LABEL = {
  determinista: "Determinista (sin LLM)",
  determinista_mejorado: "Determinista con mejoras",
  nvidia_sin_limitador: "NVIDIA sin limitador de tasa",
  nvidia: "NVIDIA + guardrail",
  nvidia_sin_guardrail: "NVIDIA sin guardrail",
  nvidia_mejorado: "NVIDIA con mejoras",
  ollama: "Ollama local",
  trafico_real: "Tráfico real (chat)",
};
const configLabel = (k) => CONFIG_LABEL[k] ?? k.replaceAll("_", " ");

const CATEGORY_LABEL = {
  base: "Pregunta base",
  perfil: "Perfil de riesgo",
  escenario_shock: "Shock de mercado",
  datos_desactualizados: "Datos desactualizados",
  variacion_linguistica: "Variación lingüística",
  activo_invalido: "Activo inválido",
  portafolio: "Portafolio completo",
  multi_turno: "Multi-turno (memoria)",
  seguridad: "Seguridad",
};
const SCENARIO_LABEL = {
  normal: "Normal",
  shock: "Shock",
  datos_desactualizados: "Datos desactualizados",
};
const NODE_ORDER = [
  "seguridad",
  "interpretar",
  "planificar",
  "agente",
  "herramientas",
  "replanificar",
  "validar",
  "persistir",
];

const pct = (v, d = 0) =>
  v === null || v === undefined
    ? "—"
    : `${(v * 100).toLocaleString("es-CL", { maximumFractionDigits: d })}%`;
const num = (v, d = 1) =>
  Number(v ?? 0).toLocaleString("es-CL", { maximumFractionDigits: d });
const ms = (v) =>
  v === null || v === undefined
    ? "—"
    : v < 1000
      ? `${num(v, 0)} ms`
      : `${num(v / 1000, v < 10000 ? 1 : 0)} s`;

function Kpi({ label, value, detail, tone }) {
  return (
    <div className={`kpi ${tone ?? ""}`}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      {detail && <span className="kpi-detail">{detail}</span>}
    </div>
  );
}

function Kpis({ m }) {
  const lat = m.latencia_turno_ms;
  return (
    <>
      <div className="kpi-row">
        <Kpi
          label="Precisión de la decisión"
          value={pct(m.precision)}
          detail={`${m.turnos_evaluados} turnos evaluados · sin guardrail ${pct(m.precision_llm_sin_guardrail)}`}
          tone={m.precision < 0.9 ? "warn" : "good"}
        />
        <Kpi
          label="Consistencia entre repeticiones"
          value={m.consistencia === null ? "—" : pct(m.consistencia)}
          detail={
            m.consistencia === null
              ? "requiere 2+ repeticiones"
              : `${m.casos_inconsistentes.length} casos inconsistentes · herramientas ${pct(m.consistencia_herramientas)}`
          }
          tone={m.consistencia !== null && m.consistencia < 1 ? "warn" : ""}
        />
        <Kpi
          label="Turnos con error o respaldo"
          value={pct(m.tasa_error + m.tasa_degradado, 1)}
          detail={`error ${pct(m.tasa_error, 1)} · modo degradado ${pct(m.tasa_degradado, 1)}`}
          tone={m.tasa_error + m.tasa_degradado > 0.05 ? "warn" : ""}
        />
        <Kpi
          label="Latencia por turno (p95)"
          value={ms(lat.p95)}
          detail={`p50 ${ms(lat.p50)} · p99 ${ms(lat.p99)} · máx ${ms(lat.max)}`}
        />
      </div>
      <div className="kpi-row">
        <Kpi
          label="Guardrail de salida"
          value={pct(m.tasa_guardrail, 1)}
          detail={`turnos corregidos · el LLM violó reglas en ${pct(m.tasa_violacion_llm, 1)}`}
        />
        <Kpi
          label="Llamadas al LLM por turno"
          value={num(m.llm_llamadas_prom)}
          detail={`${num(m.pasos_prom)} pasos · LLM = ${pct(m.proporcion_llm)} del tiempo${
            m.espera_cuota_ms?.prom
              ? ` · espera por cuota ${ms(m.espera_cuota_ms.prom)}/turno`
              : ""
          }`}
        />
        <Kpi
          label="Tokens por turno"
          value={num(m.tokens_entrada_prom + m.tokens_salida_prom, 0)}
          detail={`${num(m.tokens_entrada_prom, 0)} entrada · ${num(m.tokens_salida_prom, 0)} salida`}
        />
        <Kpi
          label="Recursos del proceso"
          value={`${num(m.rss_mb_pico, 0)} MB`}
          detail={`RAM pico · CPU ${num(m.cpu_pct_prom, 0)}% de un núcleo (${num(m.cpu_s_prom, 2)} s/turno)`}
        />
      </div>
    </>
  );
}

function Comparison({ configs, selected, onSelect }) {
  return (
    <div className="about-table-wrap">
      <table className="data-table obs-compare">
        <thead>
          <tr>
            <th>Configuración</th>
            <th className="num">Turnos</th>
            <th className="num">Precisión</th>
            <th className="num">Sin guardrail</th>
            <th className="num">Consistencia</th>
            <th className="num">p50</th>
            <th className="num">p95</th>
            <th className="num">Degradado</th>
            <th className="num">Tokens/turno</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(configs).map(([k, m]) => (
            <tr
              key={k}
              className={k === selected ? "selected" : ""}
              onClick={() => onSelect(k)}
            >
              <td>
                <button className="link-btn" onClick={() => onSelect(k)}>
                  {configLabel(k)}
                </button>
              </td>
              <td className="num">{m.turnos}</td>
              <td className="num">
                {m.turnos_evaluados ? pct(m.precision, 1) : "—"}
              </td>
              <td className="num">
                {m.turnos_evaluados
                  ? pct(m.precision_llm_sin_guardrail, 1)
                  : "—"}
              </td>
              <td className="num">
                {m.consistencia === null ? "—" : pct(m.consistencia, 1)}
              </td>
              <td className="num">{ms(m.latencia_turno_ms.p50)}</td>
              <td className="num">{ms(m.latencia_turno_ms.p95)}</td>
              <td className="num">{pct(m.tasa_degradado, 1)}</td>
              <td className="num">
                {num(m.tokens_entrada_prom + m.tokens_salida_prom, 0)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PrecisionChart({ m, baseline, baselineKey, selectedKey }) {
  const cats = Object.keys(m.precision_por_categoria);
  if (!cats.length) {
    return (
      <p className="empty-note">
        Esta configuración no tiene turnos evaluados.
      </p>
    );
  }
  const compare = baseline && baselineKey !== selectedKey;
  const rows = cats.map((c) => ({
    label: CATEGORY_LABEL[c] ?? c,
    actual: m.precision_por_categoria[c],
    base: baseline?.precision_por_categoria?.[c] ?? 0,
  }));
  const series = compare
    ? [
        { key: "base", name: configLabel(baselineKey), cls: "s1" },
        { key: "actual", name: configLabel(selectedKey), cls: "s2" },
      ]
    : [{ key: "actual", name: configLabel(selectedKey), cls: "s1" }];
  return (
    <HBarChart rows={rows} series={series} format={(v) => pct(v)} max={1} />
  );
}

function LatencyChart({ m }) {
  const rows = NODE_ORDER.filter((n) => m.latencia_nodos_ms[n]).map((n) => ({
    label: n,
    p50: m.latencia_nodos_ms[n].p50,
    p95: m.latencia_nodos_ms[n].p95,
  }));
  return (
    <HBarChart
      rows={rows}
      series={[
        { key: "p50", name: "p50 (mediana)", cls: "s1" },
        { key: "p95", name: "p95", cls: "s2" },
      ]}
      format={ms}
    />
  );
}

function ToolLatencyTable({ m }) {
  const tools = Object.entries(m.latencia_herramientas_ms).sort(
    (a, b) => b[1].p95 - a[1].p95,
  );
  return (
    <div className="about-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Herramienta</th>
            <th className="num">Llamadas</th>
            <th className="num">p50</th>
            <th className="num">p95</th>
            <th className="num">Máx</th>
            <th className="num">Errores</th>
          </tr>
        </thead>
        <tbody>
          {tools.map(([name, s]) => (
            <tr key={name}>
              <td className="mono">{name}</td>
              <td className="num">{s.n}</td>
              <td className="num">{ms(s.p50)}</td>
              <td className="num">{ms(s.p95)}</td>
              <td className="num">{ms(s.max)}</td>
              <td className="num">{m.errores_herramientas[name] ?? 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EventsTable({ m }) {
  const rows = [
    ...Object.entries(m.eventos).map(([k, v]) => ({
      k,
      v,
      turns: m.eventos_turnos?.[k] ?? v,
      kind: "Evento",
    })),
    ...Object.entries(m.violaciones).map(([k, v]) => ({
      k,
      v,
      turns: m.violaciones_turnos?.[k] ?? v,
      kind: "Violación de regla",
    })),
  ];
  if (!rows.length) {
    return (
      <p className="empty-note">Sin eventos anómalos en esta configuración.</p>
    );
  }
  return (
    <div className="about-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Tipo</th>
            <th>Evento</th>
            <th className="num">Ocurrencias</th>
            <th className="num">Turnos afectados</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.kind}-${r.k}`}>
              <td>{r.kind}</td>
              <td className="mono">{r.k}</td>
              <td className="num">{r.v}</td>
              <td className="num">{pct(r.turns / m.turnos, 1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const SEVERITY = { alta: "Alta", media: "Media", info: "Info" };

function Findings({ items }) {
  if (!items.length) return <p className="empty-note">Sin hallazgos.</p>;
  return (
    <ul className="obs-findings">
      {items.map((f, i) => (
        <li key={i} className={`obs-finding sev-${f.severidad}`}>
          <span className={`obs-sev sev-${f.severidad}`}>
            {SEVERITY[f.severidad] ?? f.severidad}
          </span>
          <div>
            <strong>{f.titulo}</strong>
            <p>{f.detalle}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function TraceExplorer({ traces, initialId }) {
  const [id, setId] = useState(initialId ?? traces[0]?.trace_id);
  const trace = traces.find((t) => t.trace_id === id) ?? traces[0];
  if (!trace) return <p className="empty-note">Sin trazas con detalle.</p>;
  return (
    <div className="obs-explorer">
      <ul
        className="obs-trace-list"
        role="listbox"
        aria-label="Turnos con detalle"
      >
        {traces.map((t) => (
          <li key={t.trace_id}>
            <button
              role="option"
              aria-selected={t.trace_id === trace.trace_id}
              className={`obs-trace-item ${t.trace_id === trace.trace_id ? "active" : ""}`}
              onClick={() => setId(t.trace_id)}
            >
              <span className="obs-trace-top">
                <span className="mono">{t.caso ?? t.trace_id}</span>
                <span className={`obs-state st-${t.estado}`}>{t.estado}</span>
                <span className="obs-trace-ms">{ms(t.latencia_ms)}</span>
              </span>
              <span className="obs-trace-q">{t.pregunta}</span>
            </button>
          </li>
        ))}
      </ul>
      <div className="obs-trace-detail">
        <div className="obs-trace-meta">
          <span>
            <b>Traza</b> <span className="mono">{trace.trace_id}</span>
          </span>
          <span>
            <b>Escenario</b>{" "}
            {SCENARIO_LABEL[trace.escenario] ?? trace.escenario}
          </span>
          <span>
            <b>Proveedor</b> {trace.proveedor ?? "—"}{" "}
            {trace.modelo ? `(${trace.modelo})` : ""}
          </span>
          <span>
            <b>Acción</b> {trace.accion}
            {trace.esperado &&
              (trace.correcto ? " ✓" : ` ✗ (esperado ${trace.esperado})`)}
          </span>
          <span>
            <b>LLM</b> {trace.llm_llamadas} llamadas ·{" "}
            {num(trace.tokens_entrada + trace.tokens_salida, 0)} tokens
          </span>
          <span>
            <b>Recursos</b> CPU {num(trace.cpu_pct, 0)}% ·{" "}
            {num(trace.rss_mb, 0)} MB
          </span>
        </div>
        <p className="obs-q">
          <b>Pregunta (enmascarada):</b> {trace.pregunta}
        </p>
        <Waterfall
          spans={trace.spans}
          total={trace.latencia_ms}
          formatMs={ms}
        />
        {(trace.eventos?.length > 0 || trace.violaciones?.length > 0) && (
          <ul className="obs-events">
            {trace.eventos.map((e, i) => (
              <li key={i}>
                <span className="mono">{e.tipo}</span> {e.detalle}
              </li>
            ))}
            {trace.violaciones.map((v) => (
              <li key={v}>
                <span className="mono">guardrail</span> {v}
                {trace.guardrail ? " (corregida)" : " (no corregida)"}
              </li>
            ))}
          </ul>
        )}
        {trace.llm_detalle?.length > 0 && (
          <div className="about-table-wrap">
            <table className="data-table obs-llm">
              <thead>
                <tr>
                  <th className="num">Paso</th>
                  <th>Proveedor</th>
                  <th className="num">Latencia</th>
                  <th className="num">Tokens</th>
                  <th>Decisión</th>
                  <th>Fallos previos</th>
                </tr>
              </thead>
              <tbody>
                {trace.llm_detalle.map((c, i) => (
                  <tr key={i}>
                    <td className="num">{c.paso}</td>
                    <td>{c.proveedor ?? "—"}</td>
                    <td className="num">{ms(c.ms)}</td>
                    <td className="num">
                      {c.tokens_entrada}/{c.tokens_salida}
                    </td>
                    <td className="mono">
                      {c.tool_calls?.join(", ") || "respuesta final"}
                    </td>
                    <td>
                      {c.fallos?.length
                        ? c.fallos
                            .map((f) => `${f.proveedor}:${f.tipo}`)
                            .join(", ")
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ObservabilityPage({ live }) {
  const [data, setData] = useState(staticData);
  const [source, setSource] = useState("estatico");
  const [error, setError] = useState(null);
  // Orden de lectura: linea base -> antes -> despues; luego lo demas
  const order = Object.keys(CONFIG_LABEL);
  const rank = (k) => (order.includes(k) ? order.indexOf(k) : order.length);
  const configs = Object.fromEntries(
    Object.entries(data.configuraciones ?? {}).sort(
      (a, b) => rank(a[0]) - rank(b[0]),
    ),
  );
  const keys = Object.keys(configs);
  // Vista enlazable: #observabilidad&config=nvidia&seccion=precision&traza=<id>
  // (muestra una sola seccion; se usa para las figuras del informe)
  const [params] = useState(
    () =>
      new URLSearchParams(window.location.hash.split("&").slice(1).join("&")),
  );
  const only = params.get("seccion");
  const show = (id) => !only || only === id;
  const [selected, setSelected] = useState(params.get("config"));
  const preferred = ["nvidia_mejorado", "nvidia"].find((k) => configs[k]);
  const current =
    selected && configs[selected]
      ? selected
      : (preferred ?? keys.find((k) => k !== "determinista") ?? keys[0]);

  useEffect(() => {
    if (!live) return;
    let cancelled = false;
    fetchObservability()
      .then((d) => {
        if (!cancelled && d.total_turnos > 0) {
          setData(d);
          setSource("vivo");
        }
      })
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [live]);

  const m = configs[current];
  const findings = (data.hallazgos ?? []).filter(
    (f) => f.configuracion === current,
  );
  const traces = (data.detalle ?? []).filter(
    (t) => t.configuracion === current,
  );

  if (!m) {
    return (
      <article className="about market">
        <p className="empty-note">
          Aún no hay trazas. Corre la evaluación (python -m
          insight_trader.observability.evaluation) o conversa con el agente.
        </p>
      </article>
    );
  }

  return (
    <article className={`about market obs ${only ? "obs-figure" : ""}`}>
      {!only && (
        <header className="about-hero">
          <span className="about-kicker">Observabilidad · EP3</span>
          <h1>¿Qué tan bien decide el agente?</h1>
          <p>
            Métricas calculadas desde las trazas de cada turno: precisión y
            consistencia de la decisión, errores, latencia por etapa y uso de
            recursos. Datos{" "}
            {source === "vivo"
              ? "en vivo desde la API local"
              : "de la última exportación"}{" "}
            · {data.total_turnos} turnos ·{" "}
            {new Date(data.generado).toLocaleString("es-CL", {
              dateStyle: "medium",
              timeStyle: "short",
            })}
            .
          </p>
          {error && (
            <p className="section-note small">
              No se pudo leer la API: {error}. Se muestran datos exportados.
            </p>
          )}
        </header>
      )}

      {!only && (
        <div
          className="obs-filters"
          role="tablist"
          aria-label="Configuración evaluada"
        >
          {keys.map((k) => (
            <button
              key={k}
              role="tab"
              aria-selected={k === current}
              className={`obs-filter ${k === current ? "active" : ""}`}
              onClick={() => setSelected(k)}
            >
              {configLabel(k)}
            </button>
          ))}
        </div>
      )}

      {show("indicadores") && (
        <section className="about-section">
          <h2>Indicadores · {configLabel(current)}</h2>
          <Kpis m={m} />
        </section>
      )}

      {show("comparacion") && (
        <section className="about-section">
          <h2>Comparación de configuraciones</h2>
          <p className="section-note">
            Mismo banco de {m.turnos_evaluados || "—"} casos con variabilidad de
            datos (perfiles, escenarios, lenguaje, seguridad). Clic en una fila
            para ver su detalle.
          </p>
          <Comparison
            configs={configs}
            selected={current}
            onSelect={setSelected}
          />
        </section>
      )}

      {show("precision") && (
        <section className="about-section">
          <h2>Precisión por tipo de caso</h2>
          <PrecisionChart
            m={m}
            baseline={configs.determinista}
            baselineKey="determinista"
            selectedKey={current}
          />
          {m.fallos_de_precision.length > 0 && (
            <details className="obs-details">
              <summary>
                {m.fallos_de_precision.length} respuestas incorrectas
              </summary>
              <ul>
                {m.fallos_de_precision.map((f) => (
                  <li key={f.trace_id}>
                    <span className="mono">{f.caso}</span> «{f.pregunta}» →{" "}
                    {f.obtenido} (esperado {f.esperado})
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}

      {show("latencia") && (
        <section className="about-section">
          <h2>Latencia por etapa del grafo</h2>
          <p className="section-note">
            Dónde se va el tiempo de cada turno. El LLM explica el{" "}
            {pct(m.proporcion_llm)} de la latencia total; la llamada individual
            al LLM tiene p50 {ms(m.latencia_llm_llamada_ms.p50)} y p95{" "}
            {ms(m.latencia_llm_llamada_ms.p95)}.
          </p>
          <LatencyChart m={m} />
          <ToolLatencyTable m={m} />
        </section>
      )}

      {show("eventos") && (
        <section className="about-section">
          <h2>Errores, eventos y reglas</h2>
          <EventsTable m={m} />
        </section>
      )}

      {show("hallazgos") && (
        <section className="about-section">
          <h2>Hallazgos del análisis de registros</h2>
          <p className="section-note">
            Detectados automáticamente sobre las trazas (cuellos de botella,
            atípicos, patrones de error).
          </p>
          <Findings items={findings} />
        </section>
      )}

      {show("trazas") && (
        <section className="about-section">
          <h2>Explorador de trazas</h2>
          <p className="section-note">
            Cascada de cada turno: nodos del grafo, herramientas y llamadas al
            LLM en el tiempo. Datos personales enmascarados y cliente
            seudonimizado.
          </p>
          <TraceExplorer
            key={current}
            traces={traces}
            initialId={params.get("traza")}
          />
        </section>
      )}
    </article>
  );
}
