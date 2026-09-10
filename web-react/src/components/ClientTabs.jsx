export default function ClientTabs({ clients, activeId, onSelect }) {
  return (
    <div className="client-tabs">
      {clients.map((c) => (
        <button
          key={c.client_id}
          className={"client-tab" + (c.client_id === activeId ? " active" : "")}
          onClick={() => onSelect(c.client_id)}
        >
          <span className="client-name">{c.client_name}</span>
          <span className="client-risk">{c.risk_category}</span>
        </button>
      ))}
    </div>
  );
}
