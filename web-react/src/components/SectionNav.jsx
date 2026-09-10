const STEPS = [
  { id: "sec-consulta", num: "01", label: "Consulta" },
  { id: "sec-analisis", num: "02", label: "Análisis" },
  { id: "sec-evidencia", num: "03", label: "Evidencia" },
  { id: "sec-recomendacion", num: "04", label: "Recomendación" },
];

function scrollToSection(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function SectionNav() {
  return (
    <nav className="section-nav" aria-label="Secciones del pipeline">
      {STEPS.map((step) => (
        <button
          key={step.id}
          className="section-nav-link"
          onClick={() => scrollToSection(step.id)}
        >
          <span className="mono">{step.num}</span>
          {step.label}
        </button>
      ))}
    </nav>
  );
}
