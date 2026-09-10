function SignalItem({ label, value, tone }) {
  return (
    <div className={"signal-item" + (tone ? " " + tone : "")}>
      <span className="k">{label}</span>
      <span className="v">{value}</span>
    </div>
  );
}

export default function SignalPills({ signal }) {
  return (
    <div className="signal-row">
      <SignalItem label="Perfil" value={signal.risk_category} />
      <SignalItem label="Tolerancia drawdown" value={`${signal.risk_tolerance.toFixed(1)}%`} />
      <SignalItem
        label="Volatilidad 7d"
        value={`${signal.volatility.toFixed(1)}%`}
        tone={signal.exceeds ? "warn" : "good"}
      />
      <SignalItem
        label="Cambio 7d"
        value={`${signal.change > 0 ? "+" : ""}${signal.change.toFixed(1)}%`}
      />
      <SignalItem label="Tendencia" value={signal.trend.replace("_", " ")} />
      <SignalItem label="Sentimiento noticias" value={signal.sentiment} />
    </div>
  );
}
