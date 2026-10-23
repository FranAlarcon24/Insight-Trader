// Etiquetas y resumenes legibles de los datos que devuelve el agente.

export const SCENARIOS = [
  {
    id: "normal",
    label: "Mercado normal",
    hint: "Datos del feed tal como llegan.",
    description:
      "Condiciones de referencia: los datos del feed simulado tal como llegan, actualizados hace 1 hora. Es la línea base con la que se comparan los demás escenarios.",
  },
  {
    id: "shock",
    label: "Shock de mercado",
    hint: "Alza inesperada de tasas: tecnología y cripto caen fuerte, el inmobiliario cae y los bonos suben como refugio.",
    description:
      "Un alza inesperada de tasas reordena los flujos: los inversionistas salen de los activos de riesgo (tecnología y cripto caen con volatilidad ×1,8), el sector inmobiliario se encarece y cae, y la renta fija sube como refugio. Pone a prueba si el agente detecta el riesgo y alerta a tiempo.",
  },
  {
    id: "datos_desactualizados",
    label: "Datos desactualizados",
    hint: "El feed de precios lleva 72 h sin actualizarse.",
    description:
      "El proveedor de precios dejó de actualizarse hace 72 horas. Los valores parecen normales, pero ya no reflejan el mercado. Pone a prueba si el agente revisa la calidad del dato antes de decidir y se abstiene de recomendar operar.",
  },
];

export const scenarioLabel = (id) =>
  SCENARIOS.find((s) => s.id === id)?.label ?? id;

export const TOOL_TYPE_LABEL = {
  consulta: "Consulta",
  razonamiento: "Razonamiento",
  escritura: "Escritura",
};

export const PRIORITY_LABEL = {
  1: "crítica",
  2: "alta",
  3: "media",
  4: "cierre",
};

export const SUGGESTIONS = [
  "¿Qué hago con TSLA?",
  "¿Y ahora?",
  "Revisa mi portafolio completo",
  "Recuerda que no quiero aumentar mi exposición a cripto",
  "¿Qué hago con ETH?",
  "¿Debería comprar NVDA?",
];

export function actionTone(action) {
  if (!action) return "muted";
  const a = action.toLowerCase();
  if (a.startsWith("reducir")) return "warn";
  if (a.startsWith("no operar")) return "amber";
  if (a.startsWith("mantener")) return "good";
  return "muted";
}

export function ruleOf(entry) {
  const match = entry.match(/^(R\d)\s+(\w+)/);
  return match ? { id: match[1], name: match[2] } : { id: "•", name: "nota" };
}

export function formatArgs(args) {
  const parts = Object.entries(args)
    .filter(
      ([key, value]) =>
        value !== null && key !== "justificacion" && key !== "consulta",
    )
    .map(([key, value]) => {
      const text = String(value);
      return `${key}: ${text.length > 48 ? `${text.slice(0, 48)}…` : text}`;
    });
  return parts.join(" · ");
}

const fileName = (path) => (path ? path.split(/[\\/]/).pop() : "");

export function summarizeResult(tool, r) {
  if (!r) return "";
  if (r.error && tool !== "consultar_portafolio") return `Error: ${r.error}`;
  switch (tool) {
    case "consultar_portafolio":
      return r.en_portafolio
        ? `${r.posicion.cantidad} unidades · ${r.posicion.peso_pct}% del portafolio · ${r.posicion.clase_activo}`
        : `${r.error}. Activos del cliente: ${r.activos_del_cliente.join(", ")}`;
    case "consultar_mercado":
      return `precio ${r.precio} · cambio 7d ${r.cambio_7d_pct}% · volatilidad ${r.volatilidad_7d_pct}% · dato de hace ${r.antiguedad_h} h${r.datos_frescos ? "" : " (DESACTUALIZADO)"}`;
    case "buscar_noticias":
      return `${r.noticias.length} noticia(s) · sentimiento ${r.sentimiento_predominante}`;
    case "recordar_memoria": {
      const prev = r.recomendacion_previa
        ? `recomendación previa: “${r.recomendacion_previa.accion}”`
        : "sin recomendación previa";
      return `${r.recuerdos_relevantes.length} recuerdo(s) · ${prev} · ${r.preferencias.length} preferencia(s)`;
    }
    case "evaluar_riesgo":
      return `volatilidad ${r.volatilidad_7d_pct}% vs tolerancia ${r.tolerancia_pct}% → ${
        r.excede_tolerancia
          ? `EXCEDE por ${Math.abs(r.margen_pct)} pts`
          : `dentro (margen ${r.margen_pct} pts)`
      }`;
    case "evaluar_concentracion":
      return (
        Object.entries(r.exposicion_por_clase)
          .map(([cls, w]) => `${cls} ${w}%`)
          .join(" · ") + ` (límite riesgo ${r.limite_pct}%)`
      );
    case "registrar_alerta":
      return `alerta ${r.severidad}: ${r.motivo}`;
    case "generar_informe":
      return `informe escrito: ${fileName(r.ruta)}`;
    case "guardar_preferencia":
      return `guardada en memoria de largo plazo: “${r.preferencia}”`;
    default:
      return JSON.stringify(r).slice(0, 120);
  }
}

export { fileName };
