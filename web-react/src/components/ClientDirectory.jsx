export default function ClientDirectory({ clients, onOpenClient }) {
  return (
    <section id="sec-clientes" className="section">
      <div className="section-head">
        <h2>Clientes</h2>
      </div>
      <p className="lede">
        3 clientes simulados con perfiles de riesgo distintos. Elige uno para
        ver su portafolio completo y las recomendaciones generadas para cada
        posición.
      </p>
      <div className="client-grid">
        {clients.map((c) => (
          <button
            key={c.client_id}
            className="client-card"
            onClick={() => onOpenClient(c.client_id)}
          >
            <div className="client-card-top">
              <span className="client-card-name serif">{c.client_name}</span>
              <span className="client-card-risk">{c.risk_category}</span>
            </div>
            <div className="client-card-meta">
              <span>{c.holdings.length} posiciones</span>
              <span>Horizonte {c.investment_horizon_years} años</span>
              <span>Tolerancia {c.risk_tolerance.toFixed(1)}%</span>
            </div>
            <p className="client-card-note">{c.notes}</p>
            <span className="client-card-cta">Ver portafolio →</span>
          </button>
        ))}
      </div>
    </section>
  );
}
