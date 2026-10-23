import { useEffect, useState } from "react";
import demo from "../data/agent_demo.json";
import { fetchRecommendations } from "./api";
import { SCENARIOS } from "./format";

const fmt = (n, digits = 1) =>
  Number(n).toLocaleString("es-CL", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

const KIND = {
  reducir: { label: "Reducir", tone: "warn" },
  no_operar: { label: "No operar", tone: "amber" },
  monitorear: { label: "Mantener y monitorear", tone: "muted" },
  mantener: { label: "Mantener", tone: "good" },
};

function Summary({ resumen }) {
  return (
    <div className="kpi-row">
      {["reducir", "no_operar", "monitorear", "mantener"].map((k) => (
        <div key={k} className={`kpi rec-kpi tone-${KIND[k].tone}`}>
          <span className="kpi-label">{KIND[k].label}</span>
          <span className="kpi-value">{resumen[k]}</span>
          <span className="kpi-detail">de {resumen.posiciones} posiciones</span>
        </div>
      ))}
    </div>
  );
}

function ClientRecommendations({ client, live, onAsk, scenarioId }) {
  return (
    <div className="rec-client">
      <div className="rec-client-head">
        <div>
          <strong>{client.client_name}</strong>
          <span className="cell-sub">
            {client.risk_category} · tolerancia {fmt(client.tolerance, 0)}%
          </span>
        </div>
        {client.urgent > 0 ? (
          <span className="rec-badge warn">
            {client.urgent} {client.urgent === 1 ? "posición" : "posiciones"}{" "}
            por reducir
          </span>
        ) : (
          <span className="rec-badge good">Sin acciones urgentes</span>
        )}
      </div>
      <ul className="rec-list">
        {client.positions.map((p) => {
          const kind = KIND[p.kind];
          return (
            <li key={p.ticker} className="rec-row">
              <div className="rec-asset">
                <strong className="mono">{p.ticker}</strong>
                <span className="cell-sub">
                  {p.name} · {fmt(p.weight)}% del portafolio
                </span>
              </div>
              <div className="rec-vol">
                <span
                  className={`mono ${p.volatility > client.tolerance ? "neg" : ""}`}
                >
                  {fmt(p.volatility)}%
                </span>
                <span className="cell-sub">volatilidad 7d</span>
              </div>
              <div className="rec-main">
                <span className={`rec-action tone-${kind.tone}`}>
                  {kind.label}
                  {p.restricted && " · sin aumentar"}
                </span>
                <p className="rec-why">{p.justification}</p>
              </div>
              {live && (
                <button
                  className="btn-secondary rec-ask"
                  onClick={() => onAsk(client.client_id, p.ticker, scenarioId)}
                >
                  Preguntar al agente
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default function RecommendationsPage({ live, activeScenario, onAsk }) {
  const [scenarioId, setScenarioId] = useState(activeScenario);
  const [fetched, setFetched] = useState({
    id: null,
    data: null,
    failed: false,
  });

  useEffect(() => {
    if (!live) return undefined;
    let cancelled = false;
    fetchRecommendations(scenarioId)
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
  const recorded = demo.recomendaciones?.[scenarioId] ?? null;
  const data = !live || current?.failed ? recorded : current?.data;

  return (
    <article className="about market">
      <header className="about-hero">
        <span className="about-kicker">Recomendaciones</span>
        <h1>Qué hacer con cada portafolio</h1>
        <p>
          La acción que sugiere el agente para cada posición de cada cliente,
          ordenada por urgencia. Usa las mismas reglas que el chat: tolerancia
          al riesgo, calidad del dato y preferencias registradas.
        </p>
      </header>

      <div
        className="rec-scenarios"
        role="radiogroup"
        aria-label="Condición de mercado"
      >
        <span className="rec-scenarios-label">
          Según la condición de mercado
        </span>
        <div className="seg-tabs">
          {SCENARIOS.map((s) => (
            <button
              key={s.id}
              role="radio"
              aria-checked={s.id === scenarioId}
              className={`seg-tab sc-${s.id} ${s.id === scenarioId ? "on" : ""}`}
              onClick={() => setScenarioId(s.id)}
            >
              <span className="sc-dot" />
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {!data ? (
        <div className="empty-note">
          <span className="spinner small" /> Calculando recomendaciones…
        </div>
      ) : (
        <>
          <Summary resumen={data.resumen} />
          {!data.datos_frescos && (
            <div className="market-warning">
              Con datos de mercado desactualizados el agente no recomienda
              operar en ninguna posición hasta recibir información fresca (regla
              R4).
            </div>
          )}
          <div className="rec-clients">
            {data.clientes.map((c) => (
              <ClientRecommendations
                key={c.client_id}
                client={c}
                live={live}
                onAsk={onAsk}
                scenarioId={scenarioId}
              />
            ))}
          </div>
        </>
      )}
    </article>
  );
}
