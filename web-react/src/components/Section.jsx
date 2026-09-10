export default function Section({ number, title, children }) {
  return (
    <section className="section">
      <div className="section-head">
        <span className="section-num mono">{number}</span>
        <h2>{title}</h2>
      </div>
      <div className="section-body">{children}</div>
    </section>
  );
}
