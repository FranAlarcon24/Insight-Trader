import { HOLDINGS_META } from "../data/holdingsMeta";

export default function Sidebar({ data, selectedTicker, onSelect }) {
  return (
    <div className="sidebar">
      <div className="label">Portafolio del cliente</div>
      {data.map((entry) => {
        const meta = HOLDINGS_META[entry.ticker];
        const active = entry.ticker === selectedTicker;
        return (
          <button
            key={entry.ticker}
            className={"holding" + (active ? " active" : "")}
            onClick={() => onSelect(entry.ticker)}
          >
            <div className="row1">
              <span className="ticker">{entry.ticker}</span>
              <span className="weight">{meta.weight.toFixed(1)}%</span>
            </div>
            <span className="name">{meta.name}</span>
            <span className="cls">{meta.cls}</span>
          </button>
        );
      })}
    </div>
  );
}
