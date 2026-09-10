function highlightNumbers(text) {
  const parts = text.split(/(\(-?\d+(?:\.\d+)?%\)|-?\d+(?:\.\d+)?%)/g);
  return parts.map((part, i) =>
    /%\)?$/.test(part) ? <b key={i}>{part}</b> : part
  );
}

export default function RecommendationCard({ recommendation }) {
  const [headline, ...rest] = recommendation.split("\n");
  const justification = rest.join(" ").replace(/^Justificacion:\s*/, "");
  const action = headline.toLowerCase().includes("reducir") ? "reduce" : "hold";
  const actionLabel = headline.split(": ")[1] || "Mantener";

  return (
    <div className={"reco action-" + action}>
      <div className="top">
        <span className="action">{actionLabel}</span>
      </div>
      <div className="body">{highlightNumbers(justification)}</div>
    </div>
  );
}
