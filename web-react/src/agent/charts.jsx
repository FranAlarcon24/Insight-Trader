import { useState } from "react";

// Graficos de los paneles de mercado. Colores por rol (--series-1/2 en
// forms.css), validados con el validador de paletas de la guia dataviz.

const fmt = (n, digits = 1) =>
  Number(n).toLocaleString("es-CL", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

/**
 * Barras horizontales de volatilidad por activo. Con `compare`, cada activo
 * muestra dos barras: mercado normal (serie 1) y el escenario (serie 2).
 */
export function VolatilityChart({ assets, compare, scenarioName }) {
  const [tip, setTip] = useState(null);
  const series = compare
    ? [
        { key: "normal_volatility_7d_pct", name: "Mercado normal", cls: "s1" },
        { key: "volatility_7d_pct", name: scenarioName, cls: "s2" },
      ]
    : [{ key: "volatility_7d_pct", name: scenarioName, cls: "s1" }];
  const max = Math.max(
    ...assets.flatMap((a) => series.map((s) => a[s.key])),
    1,
  );

  const show = (e, asset, s) => {
    const box = e.currentTarget.closest(".vchart").getBoundingClientRect();
    const bar = e.currentTarget.getBoundingClientRect();
    setTip({
      x: bar.left - box.left + bar.width,
      y: bar.top - box.top + bar.height / 2,
      value: `${fmt(asset[s.key])}%`,
      label: `${asset.ticker} · ${s.name}`,
    });
  };

  return (
    <div className="vchart">
      {compare && (
        <div className="chart-legend" aria-hidden="true">
          {series.map((s) => (
            <span key={s.key}>
              <i className={`key ${s.cls}`} /> {s.name}
            </span>
          ))}
        </div>
      )}
      <div className="vchart-rows" role="list">
        {assets.map((a) => (
          <div className="vchart-row" role="listitem" key={a.ticker}>
            <span className="vchart-label mono">{a.ticker}</span>
            <div className="vchart-bars">
              {series.map((s) => (
                <div className="vchart-track" key={s.key}>
                  <span
                    className={`vchart-bar ${s.cls}`}
                    style={{ width: `${(a[s.key] / max) * 100}%` }}
                    tabIndex={0}
                    aria-label={`${a.ticker}, ${s.name}: ${fmt(a[s.key])}%`}
                    onPointerEnter={(e) => show(e, a, s)}
                    onFocus={(e) => show(e, a, s)}
                    onPointerLeave={() => setTip(null)}
                    onBlur={() => setTip(null)}
                  />
                  <span className="vchart-value">{fmt(a[s.key])}%</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {tip && (
        <div className="chart-tip" style={{ left: tip.x + 8, top: tip.y }}>
          <strong>{tip.value}</strong>
          <span>{tip.label}</span>
        </div>
      )}
    </div>
  );
}

/**
 * Barras horizontales genericas (EP3): una fila por categoria y una barra
 * por serie. `series` = [{ key, name, cls }]; `format` formatea los valores.
 * Con mas de una serie se muestra la leyenda; cada barra lleva su valor.
 */
export function HBarChart({ rows, series, format = (v) => fmt(v), max }) {
  const [tip, setTip] = useState(null);
  const top =
    max ?? Math.max(...rows.flatMap((r) => series.map((s) => r[s.key] ?? 0)), 1);

  const show = (e, row, s) => {
    const box = e.currentTarget.closest(".vchart").getBoundingClientRect();
    const bar = e.currentTarget.getBoundingClientRect();
    setTip({
      x: bar.left - box.left + bar.width,
      y: bar.top - box.top + bar.height / 2,
      value: format(row[s.key] ?? 0),
      label: series.length > 1 ? `${row.label} · ${s.name}` : row.label,
    });
  };

  return (
    <div className="vchart">
      {series.length > 1 && (
        <div className="chart-legend" aria-hidden="true">
          {series.map((s) => (
            <span key={s.key}>
              <i className={`key ${s.cls}`} /> {s.name}
            </span>
          ))}
        </div>
      )}
      <div className="vchart-rows" role="list">
        {rows.map((r) => (
          <div className="vchart-row wide" role="listitem" key={r.label}>
            <span className="vchart-label">{r.label}</span>
            <div className="vchart-bars">
              {series.map((s) => (
                <div className="vchart-track" key={s.key}>
                  <span
                    className={`vchart-bar ${s.cls}`}
                    style={{ width: `${((r[s.key] ?? 0) / top) * 100}%` }}
                    tabIndex={0}
                    aria-label={`${r.label}, ${s.name}: ${format(r[s.key] ?? 0)}`}
                    onPointerEnter={(e) => show(e, r, s)}
                    onFocus={(e) => show(e, r, s)}
                    onPointerLeave={() => setTip(null)}
                    onBlur={() => setTip(null)}
                  />
                  <span className="vchart-value">{format(r[s.key] ?? 0)}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      {tip && (
        <div className="chart-tip" style={{ left: tip.x + 8, top: tip.y }}>
          <strong>{tip.value}</strong>
          <span>{tip.label}</span>
        </div>
      )}
    </div>
  );
}

const SPAN_CLS = { nodo: "s1", herramienta: "s2", llm: "s3" };
const SPAN_NAME = { nodo: "Nodo del grafo", herramienta: "Herramienta", llm: "Llamada al LLM" };

/**
 * Cascada de spans de un turno (como LangSmith/Langfuse): cada fila es un
 * nodo, herramienta o llamada al LLM, ubicada en el tiempo del turno.
 */
export function Waterfall({ spans, total, formatMs }) {
  const [tip, setTip] = useState(null);
  const end = Math.max(total || 0, ...spans.map((s) => s.inicio_ms + s.dur_ms), 1);
  const show = (e, s) => {
    const box = e.currentTarget.closest(".waterfall").getBoundingClientRect();
    const bar = e.currentTarget.getBoundingClientRect();
    setTip({
      x: Math.min(bar.left - box.left + bar.width, box.width - 180),
      y: bar.top - box.top + bar.height / 2,
      value: formatMs(s.dur_ms),
      label: `${SPAN_NAME[s.tipo]} · ${s.nombre} · inicio ${formatMs(s.inicio_ms)}${s.estado === "error" ? " · ERROR" : ""}`,
    });
  };
  return (
    <div className="vchart waterfall">
      <div className="chart-legend" aria-hidden="true">
        {Object.entries(SPAN_NAME).map(([k, name]) => (
          <span key={k}>
            <i className={`key ${SPAN_CLS[k]}`} /> {name}
          </span>
        ))}
      </div>
      <div className="wf-rows" role="list">
        {spans.map((s, i) => (
          <div className={`wf-row ${s.tipo}`} role="listitem" key={`${s.id}-${i}`}>
            <span className="wf-label" title={s.nombre}>
              {s.tipo === "nodo" ? "" : "↳ "}
              {s.nombre}
            </span>
            <div className="wf-track">
              <span
                className={`wf-bar ${SPAN_CLS[s.tipo]} ${s.estado === "error" ? "error" : ""}`}
                style={{
                  left: `${(s.inicio_ms / end) * 100}%`,
                  width: `max(3px, ${(s.dur_ms / end) * 100}%)`,
                }}
                tabIndex={0}
                aria-label={`${SPAN_NAME[s.tipo]} ${s.nombre}: ${formatMs(s.dur_ms)}`}
                onPointerEnter={(e) => show(e, s)}
                onFocus={(e) => show(e, s)}
                onPointerLeave={() => setTip(null)}
                onBlur={() => setTip(null)}
              />
            </div>
            <span className="wf-value">{formatMs(s.dur_ms)}</span>
          </div>
        ))}
      </div>
      {tip && (
        <div className="chart-tip" style={{ left: tip.x + 8, top: tip.y }}>
          <strong>{tip.value}</strong>
          <span>{tip.label}</span>
        </div>
      )}
    </div>
  );
}

/** Minigrafico de precios con cursor: muestra fecha y cierre del punto mas cercano. */
export function Sparkline({
  series,
  currency = "USD",
  width = 160,
  height = 40,
}) {
  const [hover, setHover] = useState(null);
  const closes = series.map((p) => p.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const pad = 3;
  const x = (i) => pad + (i / (series.length - 1)) * (width - pad * 2);
  const y = (v) =>
    pad + (1 - (v - min) / (max - min || 1)) * (height - pad * 2);
  const path = series
    .map(
      (p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.close).toFixed(1)}`,
    )
    .join(" ");

  const onMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const rel = ((e.clientX - rect.left) / rect.width) * width;
    const i = Math.round(
      ((rel - pad) / (width - pad * 2)) * (series.length - 1),
    );
    setHover(Math.max(0, Math.min(series.length - 1, i)));
  };

  const point = hover !== null ? series[hover] : null;
  return (
    <div className="spark">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
        role="img"
        aria-label={`Precio de los últimos ${series.length} días: de ${fmt(closes[0], 2)} a ${fmt(closes.at(-1), 2)} ${currency}`}
      >
        <path d={path} className="spark-line" />
        {point && (
          <>
            <line
              x1={x(hover)}
              x2={x(hover)}
              y1={0}
              y2={height}
              className="spark-cross"
            />
            <circle
              cx={x(hover)}
              cy={y(point.close)}
              r={3}
              className="spark-dot"
            />
          </>
        )}
      </svg>
      {point && (
        <div className="chart-tip spark-tip">
          <strong>
            {fmt(point.close, 2)} {currency}
          </strong>
          <span>
            {new Date(point.t * 1000).toLocaleDateString("es-CL", {
              day: "numeric",
              month: "short",
            })}
          </span>
        </div>
      )}
    </div>
  );
}
