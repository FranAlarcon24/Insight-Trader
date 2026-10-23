// Secciones informativas fijas: para que sirve, como funciona, que evalua
// y como beneficia Insight Trader.

function Hero({ kicker, title, children }) {
  return (
    <header className="about-hero">
      <span className="about-kicker">{kicker}</span>
      <h1>{title}</h1>
      <p>{children}</p>
    </header>
  );
}

function Cards({ items, className = "about-grid" }) {
  return (
    <div className={className}>
      {items.map((c) => (
        <div key={c.title} className={`about-card ${c.tone ?? ""}`}>
          <h3>{c.title}</h3>
          {c.text && <p>{c.text}</p>}
          {c.list && (
            <ul>
              {c.list.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

function Checks({ items }) {
  return (
    <ul className="about-checks">
      {items.map((t) => (
        <li key={t}>{t}</li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------ ¿Para qué sirve? */

function ParaQueSirve() {
  return (
    <article className="about">
      <Hero
        kicker="¿Para qué sirve?"
        title="Un copiloto para asesores de inversión"
      >
        Insight Trader revisa las posiciones de cada cliente frente al mercado y
        a su perfil de riesgo, y recomienda qué hacer explicando siempre el
        porqué con datos concretos.
      </Hero>

      <section className="about-section">
        <h2>El problema</h2>
        <Cards
          items={[
            {
              title: "Recomendaciones sin explicación",
              text: "Los clientes reciben sugerencias de “comprar” o “vender” sin entender por qué. Eso genera desconfianza y dificulta cumplir las exigencias de transparencia de la asesoría algorítmica.",
            },
            {
              title: "Asesores sin tiempo",
              text: "Un asesor no alcanza a revisar a diario cada portafolio frente a un mercado que cambia. Los riesgos se detectan tarde, cuando el cliente ya perdió más de lo que toleraba.",
            },
          ]}
        />
      </section>

      <section className="about-section">
        <h2>La solución</h2>
        <p>
          Un agente de IA que hace esa revisión de forma automática y trazable:
          consulta el portafolio, el mercado y las noticias, cruza todo con el
          perfil del cliente, alerta al asesor cuando algo se sale de lo
          tolerable y deja un informe escrito de cada decisión.
        </p>
      </section>

      <section className="about-section">
        <h2>Para quién</h2>
        <Cards
          items={[
            {
              title: "Asesores de inversión",
              text: "Usuarios principales: conversan con el agente sobre cada cliente y reciben alertas priorizadas.",
            },
            {
              title: "Clientes de la fintech",
              text: "Reciben recomendaciones que entienden, con las cifras que las respaldan.",
            },
            {
              title: "Áreas de riesgo y cumplimiento",
              text: "Cuentan con un registro de qué se recomendó, con qué datos y bajo qué reglas.",
            },
          ]}
          className="about-grid three"
        />
      </section>

      <section className="about-section">
        <h2>Alcance</h2>
        <Cards
          className="about-columns"
          items={[
            {
              title: "Qué hace",
              tone: "good",
              list: [
                "Revisa una posición o el portafolio completo de un cliente.",
                "Recomienda mantener, reducir o no operar, citando las cifras usadas.",
                "Alerta al asesor y genera un informe escrito.",
                "Recuerda preferencias y recomendaciones previas.",
              ],
            },
            {
              title: "Qué no hace",
              tone: "muted",
              list: [
                "No ejecuta órdenes de compra o venta: solo recomienda.",
                "No recomienda activos que el cliente no tiene.",
                "No predice precios ni garantiza rentabilidad.",
                "No reemplaza el juicio del asesor.",
              ],
            },
          ]}
        />
      </section>
    </article>
  );
}

/* ------------------------------------------------------------------ ¿Cómo funciona? */

const STEPS = [
  {
    title: "Interpreta",
    text: "Identifica el activo o la revisión que se pide. Si es una pregunta de seguimiento (“¿y ahora?”), recuerda el activo de la conversación.",
  },
  {
    title: "Planifica",
    text: "Arma un plan de tareas con prioridades: primero validar (P1), luego reunir evidencia (P2–P3) y al final escribir el informe (P4).",
  },
  {
    title: "Ejecuta y se adapta",
    text: "Llama a sus herramientas una por una. Después de cada resultado re-planifica: agrega una alerta si el riesgo supera la tolerancia, o cancela el análisis si los datos están desactualizados.",
  },
  {
    title: "Responde y recuerda",
    text: "Entrega la recomendación con los datos que la respaldan, registra alertas e informe y guarda la interacción en su memoria.",
  },
];

function ComoFunciona() {
  return (
    <article className="about">
      <Hero
        kicker="¿Cómo funciona?"
        title="Un agente que planifica, actúa y se corrige"
      >
        A diferencia de un chatbot que solo responde, Insight Trader sigue un
        plan, usa herramientas para obtener datos reales del sistema y ajusta su
        plan según lo que encuentra.
      </Hero>

      <section className="about-section">
        <h2>El flujo de cada consulta</h2>
        <ol className="about-steps">
          {STEPS.map((s, i) => (
            <li key={s.title}>
              <span className="about-step-num">{i + 1}</span>
              <div>
                <strong>{s.title}</strong>
                <p>{s.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="about-section">
        <h2>Sus herramientas</h2>
        <Cards
          className="about-grid three"
          items={[
            {
              title: "Consulta",
              list: [
                "Portafolio y perfil del cliente",
                "Datos de mercado y su frescura",
                "Noticias con sentimiento",
                "Memoria de interacciones previas",
              ],
            },
            {
              title: "Razonamiento",
              list: [
                "Riesgo del activo frente a la tolerancia",
                "Concentración del portafolio",
              ],
            },
            {
              title: "Escritura",
              list: [
                "Alertas para el asesor",
                "Informe de la recomendación",
                "Preferencias del cliente",
              ],
            },
          ]}
        />
      </section>

      <section className="about-section">
        <h2>Su memoria</h2>
        <Cards
          className="about-columns"
          items={[
            {
              title: "Corto plazo",
              text: "Recuerda el contexto de la conversación actual, por ejemplo el activo del que se está hablando. Se reinicia con “Nueva conversación”.",
            },
            {
              title: "Largo plazo",
              text: "Guarda entre sesiones las recomendaciones dadas y las preferencias declaradas por cada cliente, y las recupera por similitud con la pregunta.",
            },
          ]}
        />
      </section>

      <section className="about-section">
        <h2>Por qué está diseñado así</h2>
        <Cards
          items={[
            {
              title: "Reglas críticas fuera del modelo de lenguaje",
              text: "En finanzas, controles como “no operar con datos viejos” no pueden depender de que la IA los recuerde. Viven en el planificador y se cumplen siempre.",
            },
            {
              title: "Todo queda trazado",
              text: "Cada herramienta usada, cada resultado y cada ajuste del plan se muestran en pantalla y quedan registrados. Así cualquier recomendación se puede auditar.",
            },
            {
              title: "Datos antes que redacción",
              text: "El agente primero reúne evidencia con sus herramientas y recién después redacta. La respuesta solo puede citar cifras que efectivamente obtuvo.",
            },
            {
              title: "Modelo de IA intercambiable",
              text: "Funciona con un modelo simulado sin costo o con un modelo real (Claude), sin cambiar el resto del sistema. Construido con LangGraph y LangChain.",
            },
          ]}
        />
      </section>
    </article>
  );
}

/* ------------------------------------------------------------------ ¿Qué evaluamos? */

const VARIABLES = [
  [
    "Volatilidad a 7 días",
    "Feed de mercado",
    "Se compara con la tolerancia del cliente. Si la supera: alerta y recomendación de reducir.",
  ],
  [
    "Tolerancia a drawdown",
    "Perfil del cliente",
    "Pérdida máxima que el cliente declara soportar. Es el límite de referencia.",
  ],
  [
    "Cambio semanal y tendencia",
    "Feed de mercado",
    "Distingue un alza sostenida de una caída. Una caída de 10% o más vuelve crítica la alerta.",
  ],
  [
    "Sentimiento de noticias",
    "Noticias (búsqueda semántica)",
    "Complementa la lectura del mercado: noticias negativas refuerzan la cautela.",
  ],
  [
    "Concentración",
    "Portafolio del cliente",
    "Peso en tecnología o cripto frente al límite del perfil: 25% conservador, 40% moderado, 70% agresivo.",
  ],
  [
    "Frescura del dato",
    "Feed de mercado",
    "Si los precios tienen más de 24 h, el agente no recomienda operar.",
  ],
  [
    "Preferencias",
    "Memoria de largo plazo",
    "Restricciones declaradas por el cliente, como no aumentar la exposición a cripto.",
  ],
  [
    "Historial",
    "Memoria de largo plazo",
    "La recomendación anterior para el mismo activo: el agente explica si su decisión cambia.",
  ],
];

const RULES = [
  ["R0", "Contexto", "Sin activo en la pregunta: usa el del turno anterior."],
  [
    "R1",
    "Validación",
    "Activo fuera del portafolio: cancela el plan y no recomienda.",
  ],
  [
    "R2",
    "Memoria",
    "Hay una recomendación previa: explica si cambia y por qué.",
  ],
  [
    "R3",
    "Riesgo",
    "Volatilidad sobre la tolerancia: alerta y evalúa la concentración.",
  ],
  [
    "R4",
    "Calidad de datos",
    "Datos con más de 24 h: cancela el análisis y responde “no operar”.",
  ],
  [
    "R5",
    "Concentración",
    "Exposición a tecnología o cripto sobre el límite del perfil: alerta.",
  ],
  [
    "R6",
    "Preferencia",
    "Preferencia registrada aplicable: no recomienda aumentar exposición.",
  ],
];

const GLOSSARY = [
  [
    "Volatilidad",
    "Cuánto varía el precio de un activo; mide qué tan inestable está.",
  ],
  [
    "Drawdown",
    "Caída desde un máximo hasta un mínimo. La tolerancia indica cuánta caída acepta el cliente.",
  ],
  ["Concentración", "Porcentaje del portafolio en una misma clase de activo."],
  [
    "Re-planificación",
    "Ajuste del plan del agente a partir de lo que observa en cada paso.",
  ],
];

function QueEvaluamos() {
  return (
    <article className="about">
      <Hero
        kicker="¿Qué evaluamos?"
        title="Las señales detrás de cada recomendación"
      >
        El agente cruza el perfil de riesgo de cada cliente con el estado del
        mercado. Estas son las variables que mira, de dónde las obtiene y cómo
        influyen en su decisión.
      </Hero>

      <section className="about-section">
        <h2>Variables</h2>
        <div className="about-table-wrap">
          <table className="about-table vars">
            <thead>
              <tr>
                <th>Variable</th>
                <th>Fuente</th>
                <th>Cómo se usa</th>
              </tr>
            </thead>
            <tbody>
              {VARIABLES.map(([name, source, use]) => (
                <tr key={name}>
                  <td>
                    <strong>{name}</strong>
                  </td>
                  <td>{source}</td>
                  <td>{use}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="about-section">
        <h2>Posibles recomendaciones</h2>
        <Cards
          className="about-grid three"
          items={[
            {
              title: "Mantener",
              tone: "good",
              text: "El riesgo del activo está dentro de lo que el cliente tolera.",
            },
            {
              title: "Reducir posición",
              tone: "warn",
              text: "La volatilidad supera la tolerancia del cliente: se prioriza preservar capital.",
            },
            {
              title: "No operar",
              tone: "amber",
              text: "Los datos no son confiables (desactualizados): mejor esperar información fresca.",
            },
          ]}
        />
      </section>

      <section className="about-section">
        <h2>Reglas de decisión</h2>
        <table className="about-table">
          <tbody>
            {RULES.map(([id, name, text]) => (
              <tr key={id}>
                <td className="mono">{id}</td>
                <td>
                  <strong>{name}</strong>
                </td>
                <td>{text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="about-section">
        <h2>Condiciones de mercado simuladas</h2>
        <Cards
          className="about-grid three"
          items={[
            {
              title: "Mercado normal",
              text: "Los datos del feed tal como llegan.",
            },
            {
              title: "Shock de mercado",
              text: "Alza de tasas: tecnología y cripto caen fuerte, el inmobiliario cae y los bonos suben como refugio.",
            },
            {
              title: "Datos desactualizados",
              text: "El feed lleva 72 h sin actualizarse: el agente debe detectarlo y abstenerse.",
            },
          ]}
        />
      </section>

      <section className="about-section">
        <h2>Glosario</h2>
        <dl className="about-glossary">
          {GLOSSARY.map(([term, def]) => (
            <div key={term}>
              <dt>{term}</dt>
              <dd>{def}</dd>
            </div>
          ))}
        </dl>
      </section>
    </article>
  );
}

/* ------------------------------------------------------------------ ¿Cómo te beneficia? */

function ComoTeBeneficia() {
  return (
    <article className="about">
      <Hero
        kicker="¿Cómo te beneficia?"
        title="Más control, menos riesgo, decisiones explicables"
      >
        Insight Trader no reemplaza al asesor: le da tiempo, visibilidad y
        respaldo para tomar mejores decisiones con cada cliente.
      </Hero>

      <section className="about-section">
        <h2>Beneficios</h2>
        <Cards
          className="about-grid three"
          items={[
            {
              title: "Para el asesor",
              list: [
                "Revisa un portafolio completo en segundos.",
                "Recibe alertas priorizadas por gravedad.",
                "Detecta riesgos antes de que el cliente los sufra.",
                "Cuenta con un informe listo para la reunión.",
              ],
            },
            {
              title: "Para el cliente",
              list: [
                "Entiende el porqué de cada recomendación.",
                "Sus preferencias se recuerdan y se respetan.",
                "Recibe consejos acordes a su tolerancia real al riesgo.",
              ],
            },
            {
              title: "Para la fintech",
              list: [
                "Transparencia y trazabilidad para cumplimiento.",
                "Criterios consistentes entre asesores.",
                "Escala la asesoría sin perder control humano.",
              ],
            },
          ]}
        />
      </section>

      <section className="about-section">
        <h2>Buenas prácticas de uso</h2>
        <Checks
          items={[
            "Atender primero las alertas críticas y altas.",
            "Verificar que los datos de mercado estén frescos antes de decidir.",
            "Mantener actualizado el perfil de riesgo y registrar las preferencias del cliente.",
            "Revisar la traza (plan, herramientas y re-planificaciones) para entender cada recomendación.",
            "Usar la recomendación como insumo para conversar con el cliente, no como una instrucción.",
          ]}
        />
      </section>

      <section className="about-section">
        <h2>Riesgos y limitaciones</h2>
        <Cards
          items={[
            {
              title: "Datos simulados",
              text: "Clientes, precios y noticias son ficticios: ilustran el funcionamiento, no el mercado real.",
            },
            {
              title: "Modelo de riesgo simplificado",
              text: "Compara la volatilidad semanal con la tolerancia. Es útil pero parcial: no considera correlaciones ni liquidez.",
            },
            {
              title: "Umbrales fijos",
              text: "Límites como 24 h de frescura o el tope de concentración por perfil son reglas generales que pueden no calzar con todos los clientes.",
            },
            {
              title: "Sesgo de automatización",
              text: "Una respuesta bien redactada puede generar exceso de confianza. Toda recomendación debe revisarla un asesor.",
            },
          ]}
        />
      </section>
    </article>
  );
}

const PAGES = {
  "para-que-sirve": ParaQueSirve,
  "como-funciona": ComoFunciona,
  "que-evaluamos": QueEvaluamos,
  "como-te-beneficia": ComoTeBeneficia,
};

export default function InfoPage({ page }) {
  const Page = PAGES[page];
  return Page ? <Page /> : null;
}
