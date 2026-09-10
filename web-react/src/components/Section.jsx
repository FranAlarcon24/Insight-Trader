export default function Section({ id, number, title, children }) {
  return (
    <section id={id} className="section">
      <div className="section-head">
        <span className="section-num mono">{number}</span>
        <h2>{title}</h2>
      </div>
      <div className="section-body">{children}</div>
    </section>
  );
}
