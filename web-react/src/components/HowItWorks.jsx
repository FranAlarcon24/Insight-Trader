const STEPS = [
  {
    num: "01",
    title: "Consulta",
    text: "El cliente pregunta por un activo de su portafolio (ej. “¿Debería mantener mi posición en TSLA?”).",
  },
  {
    num: "02",
    title: "Análisis riesgo-mercado",
    text: "Un agente cruza el perfil de riesgo declarado por el cliente con la volatilidad y tendencia actual del activo.",
  },
  {
    num: "03",
    title: "Evidencia recuperada (RAG)",
    text: "Se recuperan datos concretos de dos fuentes: el portafolio e historial del cliente (interna) y el mercado y noticias (externa).",
  },
  {
    num: "04",
    title: "Recomendación generada",
    text: "Un modelo de lenguaje redacta la recomendación final citando los datos recuperados — nunca inventa cifras.",
  },
];

export default function HowItWorks() {
  return (
    <section id="sec-como-funciona" className="section">
      <div className="section-head">
        <h2>¿Cómo funciona?</h2>
      </div>
      <p className="lede">
        Insight Trader es un copiloto de trading explicable: en vez de una
        recomendación sin contexto, cada respuesta pasa por un pipeline de
        4 agentes que deja evidencia de por qué se sugiere comprar, vender o
        mantener una posición.
      </p>
      <ol className="how-steps">
        {STEPS.map((step) => (
          <li key={step.num} className="how-step">
            <span className="how-num mono">{step.num}</span>
            <div>
              <h3>{step.title}</h3>
              <p>{step.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
