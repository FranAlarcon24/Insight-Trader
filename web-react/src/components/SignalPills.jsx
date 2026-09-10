function Pill({ label, value, tone }) {
  return (
    <div className={"pill" + (tone ? " " + tone : "")}>
      <span className="k">{label}</span>
      <span className="v">{value}</span>
    </div>
  );
}

export default function SignalPills({ signal }) {
  return (
    <div className="signal-strip">
      <Pill label="Perfil" value={signal.risk_category} />
      <Pill label="Tolerancia drawdown" value={`${signal.risk_tolerance.toFixed(1)}%`} />
      <Pill
        label="Volatilidad 7d"
        value={`${signal.volatility.toFixed(1)}%`}
        tone={signal.exceeds ? "warn" : "good"}
      />
      <Pill
        label="Cambio 7d"
        value={`${signal.change > 0 ? "+" : ""}${signal.change.toFixed(1)}%`}
      />
      <Pill label="Tendencia" value={signal.trend.replace("_", " ")} />
      <Pill label="Sentimiento noticias" value={signal.sentiment} />
    </div>
  );
}
