export default function Sidebar({ holdings, selectedTicker, onSelect }) {
  return (
    <div className="sidebar">
      <div className="label">Portafolio del cliente</div>
      {holdings.map((h) => {
        const active = h.ticker === selectedTicker;
        return (
          <button
            key={h.ticker}
            className={"holding" + (active ? " active" : "")}
            onClick={() => onSelect(h.ticker)}
          >
            <div className="row1">
              <span className="ticker">{h.ticker}</span>
              <span className="weight">{h.weight.toFixed(1)}%</span>
            </div>
            <span className="name">{h.name}</span>
            <span className="cls">{h.asset_class}</span>
          </button>
        );
      })}
    </div>
  );
}
