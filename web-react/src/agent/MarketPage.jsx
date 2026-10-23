import { useEffect, useState } from "react";
import demo from "../data/agent_demo.json";
import { fetchMarket, fetchRealMarket } from "./api";
import { Sparkline, VolatilityChart } from "./charts";
import { SCENARIOS } from "./format";

const fmt = (n, digits = 1) =>
  Number(n).toLocaleString("es-CL", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
const signed = (n) => `${n > 0 ? "+" : ""}${fmt(n)}`;

const TREND_LABEL = {
  alza_fuerte: "Alza fuerte",
  alza: "Alza",
  estable: "Estable",
  baja: "Baja",
  baja_fuerte: "Baja fuerte",
};
const SENTIMENT_TONE = { positivo: "good", negativo: "warn", neutral: "muted" };

function Kpi({ label, value, detail, tone }) {
  return (
    <div className={`kpi ${tone ?? ""}`}>
      <span className="kpi-label">{label}</span>
      <span className="kpi-value">{value}</span>
      {detail && <span className="kpi-detail">{detail}</span>}
    </div>
  );
}

function Delta({ value, base, invert = false }) {
  const diff = Math.round((value - base) * 10) / 10;
  if (diff === 0) return <span className="delta same">sin cambio</span>;
  const worse = invert ? diff < 0 : diff > 0;
  return (
    <span className={`delta ${worse ? "worse" : "better"}`}>
      {signed(diff)} pts
    </span>
  );
}

/** Accion recomendada para un cliente en el escenario (misma logica que el agente). */
function clientAction(c, fresh) {
  if (!fresh) {
    return {
      tone: "amber",
      action: "No operar",
      detail: "Esperar datos de mercado frescos antes de mover el portafolio.",
    };
  }
  if (c.positions_over.length === 0) {
    return {
      tone: "good",
      action: "Mantener",
      detail: `Ninguna posición supera su tolerancia de ${fmt(c.tolerance, 0)}%.`,
    };
  }
  const tickers = [...c.positions_over]
    .sort((a, b) => b.volatility - a.volatility)
    .map((p) => p.ticker);
  return {
    tone: "warn",
    action: `Reducir ${tickers.join(", ")}`,
    detail: `${fmt(c.weight_at_risk)}% del portafolio supera su tolerancia de ${fmt(c.tolerance, 0)}%.`,
  };
}

function ClientImpact({ clients, fresh }) {
  const affected = clients.filter((c) => c.weight_at_risk > 0);
  const worst = [...clients].sort(
    (a, b) => b.weight_at_risk - a.weight_at_risk,
  )[0];
  const summary = !fresh
    ? "Con datos de más de 24 h el agente no recomienda operar a ningún cliente: primero hay que recuperar información confiable."
    : affected.length === 0
      ? "Ningún cliente tiene posiciones sobre su tolerancia: el portafolio de todos se mantiene."
      : `${affected.length} de ${clients.length} clientes tienen posiciones sobre su tolerancia. El más expuesto es ${worst.client_name}, con ${fmt(worst.weight_at_risk)}% de su portafolio en riesgo.`;

  return (
    <section className="about-section">
      <h2>¿Qué significa para tus clientes?</h2>
      <p className={`impact-summary ${fresh ? "" : "stale"}`}>{summary}</p>
      <div className="impact-grid">
        {clients.map((c) => {
          const rec = clientAction(c, fresh);
          return (
            <div key={c.client_id} className="impact-card">
              <div className="impact-head">
                <strong>{c.client_name}</strong>
                <span className="cell-sub">
                  {c.risk_category} · tolerancia {fmt(c.tolerance, 0)}%
                </span>
              </div>
              <div className={`impact-action tone-${rec.tone}`}>
                <span className="impact-action-label">Acción sugerida</span>
                <strong>{rec.action}</strong>
              </div>
              <p className="impact-detail">{rec.detail}</p>
              {fresh && (
                <>
                  <div
                    className="meter"
                    role="img"
                    aria-label={`${fmt(c.weight_at_risk)}% del portafolio en riesgo`}
                  >
                    <span
                      style={{ width: `${Math.min(c.weight_at_risk, 100)}%` }}
                    />
                  </div>
                  {c.positions_over.length === 0 ? (
                    <div className="impact-chips">
                      <span className="chip-ok">Sin posiciones en riesgo</span>
                    </div>
                  ) : (
                    <table className="risk-list">
                      <thead>
                        <tr>
                          <th>Activo</th>
                          <th className="num">Volatilidad</th>
                          <th className="num">Peso</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...c.positions_over]
                          .sort((a, b) => b.volatility - a.volatility)
                          .map((p) => (
                            <tr key={p.ticker}>
                              <td className="mono">{p.ticker}</td>
                              <td className="num neg">{fmt(p.volatility)}%</td>
                              <td className="num">{fmt(p.weight)}%</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function RealMarket({ live }) {
  const [state, setState] = useState({
    loading: live,
    data: null,
    failed: false,
  });

  useEffect(() => {
    if (!live) return undefined;
    let cancelled = false;
    fetchRealMarket()
      .then(
        (data) =>
          !cancelled &&
          setState({
            loading: false,
            data: data.activos.length ? data : null,
            failed: !data.activos.length,
          }),
      )
      .catch(
        () =>
          !cancelled && setState({ loading: false, data: null, failed: true }),
      );
    return () => {
      cancelled = true;
    };
  }, [live]);

  return (
    <section className="about-section">
      <div className="section-head-row">
        <h2>Mercado real · referencia</h2>
        <span className="source-chip">API pública · Yahoo Finance</span>
      </div>
      <p className="section-note">
        Precios reales de los mismos activos, para contrastar con la simulación.
        El agente trabaja con el feed simulado para que cada demostración sea
        reproducible.
      </p>
      {(!live || state.failed) && (
        <div className="empty-note">
          Los datos reales se muestran cuando la API del agente está en
          ejecución y tiene acceso a internet.
        </div>
      )}
      {state.loading && (
        <div className="empty-note">
          <span className="spinner small" /> Consultando precios reales…
        </div>
      )}
      {state.data && (
        <>
          <div className="about-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Activo</th>
                  <th className="num">Precio</th>
                  <th className="num">Cambio 7d</th>
                  <th className="num">Volatilidad 7d</th>
                  <th>Últimos 30 días</th>
                </tr>
              </thead>
              <tbody>
                {state.data.activos.map((a) => (
                  <tr key={a.ticker}>
                    <td>
                      <strong className="mono">{a.ticker}</strong>
                      <span className="cell-sub mono">{a.symbol}</span>
                    </td>
                    <td className="num mono">
                      {fmt(a.price, 2)}{" "}
                      <span className="cell-sub">{a.currency}</span>
                    </td>
                    <td
                      className={`num mono ${a.change_7d_pct < 0 ? "neg" : "pos"}`}
                    >
                      {signed(a.change_7d_pct)}%
                    </td>
                    <td className="num mono">{fmt(a.volatility_7d_pct)}%</td>
                    <td>
                      <Sparkline series={a.series} currency={a.currency} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="section-note small">
            {state.data.desde_cache ? "Último dato guardado" : "Consultado"}:{" "}
            {new Date(state.data.consultado).toLocaleString("es-CL")} ·
            Volatilidad 7d = desviación estándar de los retornos diarios de la
            última semana, escalada a la semana.
          </p>
        </>
      )}
    </section>
  );
}

export default function MarketPage({
  scenarioId,
  live,
  activeScenario,
  onActivate,
}) {
  const scenario = SCENARIOS.find((s) => s.id === scenarioId);
  const recorded = demo.mercado?.[scenarioId] ?? null;
  const [fetched, setFetched] = useState({
    id: null,
    data: null,
    failed: false,
  });

  useEffect(() => {
    if (!live) return undefined;
    let cancelled = false;
    fetchMarket(scenarioId)
      .then(
        (data) =>
          !cancelled && setFetched({ id: scenarioId, data, failed: false }),
      )
      .catch(
        () =>
          !cancelled &&
          setFetched({ id: scenarioId, data: null, failed: true }),
      );
    return () => {
      cancelled = true;
    };
  }, [live, scenarioId]);

  const current = fetched.id === scenarioId ? fetched : null;
  // Si la API no responde (o es una version antigua sin esta ruta) se usan
  // los datos exportados del escenario: la pagina nunca queda vacia.
  const usingFallback = live && current?.failed;
  const data = !live || usingFallback ? recorded : current?.data;
  const isActive = activeScenario === scenarioId;
  const compare = scenarioId !== "normal";

  return (
    <article className="about market">
      <header className="about-hero market-hero">
        <div className="market-hero-top">
          <span className={`about-kicker sc-${scenarioId}`}>
            <span className="sc-dot" /> Simulación de mercado
          </span>
          {live && !isActive && (
            <button
              className="btn-primary"
              onClick={() => onActivate(scenarioId)}
            >
              Usar este escenario en el chat
            </button>
          )}
        </div>
        <h1>{scenario.label}</h1>
        <p>{scenario.description}</p>
      </header>

      {!data && (
        <div className="empty-note">
          <span className="spinner small" /> Cargando métricas del escenario…
        </div>
      )}

      {data && (
        <>
          <div className="kpi-row">
            <Kpi
              label="Volatilidad promedio"
              value={`${fmt(data.volatilidad_promedio)}%`}
              detail={
                compare ? (
                  <Delta
                    value={data.volatilidad_promedio}
                    base={data.volatilidad_promedio_normal}
                  />
                ) : (
                  "Línea base"
                )
              }
            />
            <Kpi
              label="Activos en baja (7d)"
              value={`${data.activos.filter((a) => a.change_7d_pct < 0).length} de ${data.activos.length}`}
              detail="Cambio semanal negativo"
            />
            <Kpi
              label="Antigüedad del dato"
              value={`${fmt(data.antiguedad_h)} h`}
              detail={
                data.datos_frescos
                  ? "Dato fresco"
                  : `Supera el límite de ${data.limite_frescura_h} h`
              }
              tone={data.datos_frescos ? "good" : "warn"}
            />
            <Kpi
              label="Clientes con riesgo"
              value={
                data.datos_frescos
                  ? `${data.clientes.filter((c) => c.weight_at_risk > 0).length} de ${data.clientes.length}`
                  : "No evaluable"
              }
              detail={
                data.datos_frescos
                  ? "Con posiciones sobre su tolerancia"
                  : "El agente no evalúa riesgo con datos viejos"
              }
            />
          </div>

          <ClientImpact clients={data.clientes} fresh={data.datos_frescos} />

          <section className="about-section">
            <h2>Activos</h2>
            <div className="about-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Activo</th>
                    <th className="num">Precio</th>
                    <th className="num">Cambio 7d</th>
                    <th className="num">Volatilidad 7d</th>
                    <th>Tendencia</th>
                    <th>Noticias</th>
                  </tr>
                </thead>
                <tbody>
                  {data.activos.map((a) => (
                    <tr key={a.ticker}>
                      <td>
                        <strong className="mono">{a.ticker}</strong>
                        <span className="cell-sub">{a.name}</span>
                      </td>
                      <td className="num mono">{fmt(a.price, 2)}</td>
                      <td className="num">
                        <span
                          className={`mono ${a.change_7d_pct < 0 ? "neg" : "pos"}`}
                        >
                          {signed(a.change_7d_pct)}%
                        </span>
                        {compare && (
                          <Delta
                            value={a.change_7d_pct}
                            base={a.normal_change_7d_pct}
                            invert
                          />
                        )}
                      </td>
                      <td className="num">
                        <span className="mono">
                          {fmt(a.volatility_7d_pct)}%
                        </span>
                        {compare && (
                          <Delta
                            value={a.volatility_7d_pct}
                            base={a.normal_volatility_7d_pct}
                          />
                        )}
                      </td>
                      <td>{TREND_LABEL[a.trend] ?? a.trend}</td>
                      <td>
                        <span
                          className={`sentiment ${SENTIMENT_TONE[a.sentiment] ?? "muted"}`}
                        >
                          {a.sentiment}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="about-section">
            <h2>Volatilidad a 7 días por activo</h2>
            <VolatilityChart
              assets={data.activos}
              compare={compare}
              scenarioName={scenario.label}
            />
          </section>

          <section className="about-section">
            <h2>Noticias del escenario</h2>
            <ul className="news-list">
              {data.noticias.map((n) => (
                <li key={`${n.ticker}-${n.headline}`}>
                  <span
                    className={`sentiment ${SENTIMENT_TONE[n.sentiment] ?? "muted"}`}
                  >
                    {n.sentiment}
                  </span>
                  <span className="mono news-ticker">{n.ticker}</span>
                  <span className="news-headline">{n.headline}</span>
                  <span className="cell-sub">{n.date}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}

      <RealMarket live={live} />
    </article>
  );
}
