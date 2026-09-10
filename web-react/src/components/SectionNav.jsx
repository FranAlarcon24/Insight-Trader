function scrollToSection(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

export default function SectionNav({ links }) {
  return (
    <nav className="section-nav" aria-label="Navegación de secciones">
      {links.map((link) =>
        link.onClick ? (
          <button key={link.id} className="section-nav-link" onClick={link.onClick}>
            {link.label}
          </button>
        ) : (
          <button
            key={link.id}
            className="section-nav-link"
            onClick={() => scrollToSection(link.id)}
          >
            {link.num && <span className="mono">{link.num}</span>}
            {link.label}
          </button>
        )
      )}
    </nav>
  );
}
