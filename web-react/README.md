# Insight Trader — Interfaz web del agente

Aplicación React (Vite) con interfaz de asistente para el agente LangGraph de Insight Trader (Evaluación Parcial 2). No reimplementa lógica de negocio: muestra lo que hace el agente Python.

Al entrar se elige el cliente que se va a asesorar. Luego se conversa con el agente, y cada respuesta muestra:

- el **plan de ejecución** (checklist con prioridades P1–P4),
- las **llamadas a herramientas** de consulta, razonamiento y escritura, con su resultado (clic para ver el JSON),
- las **re-planificaciones** (reglas R0–R6),
- la **recomendación final**, con las alertas enviadas al asesor y el informe generado.

En la barra lateral se elige el cliente y la **simulación de mercado** (normal, shock o datos desactualizados). El botón **Contexto del cliente** abre el perfil, las posiciones y la memoria de largo plazo.

## Modos

- **En vivo.** Consume la API Python del agente (`python -m insight_trader.agent.server`, puerto 8000). En desarrollo, Vite la redirige como `/api` (ver `vite.config.js`).
- **Grabado.** Si la API no responde (por ejemplo, en el despliegue estático de Vercel), reproduce conversaciones reales guardadas en `src/data/agent_demo.json`. Para regenerarlas, ejecutar desde la raíz del repo:

```powershell
python scripts/export_agent_demo.py
```

## Estructura

```
src/
  App.jsx               # Monta la vista del agente
  agent/
    AgentView.jsx       # Estructura de la app: barra lateral, chat, panel de contexto
    AgentTurn.jsx       # Una respuesta del agente: plan, herramientas, re-planificación, resultado
    InfoPages.jsx       # Secciones: ¿Cómo funciona?, ¿Para qué sirve?, ¿Qué evaluamos?, ¿Cómo te beneficia?
    NewClientModal.jsx  # Formulario para crear clientes
    api.js              # Cliente de la API Python
    format.js           # Etiquetas y resúmenes legibles de los resultados
    icons.jsx           # Iconos SVG y logotipo
    agent.css           # Estilos
  data/agent_demo.json  # Conversaciones para el modo grabado
```

## Desarrollo

```powershell
npm install       # solo la primera vez
npm run dev       # servidor de desarrollo (requiere la API Python para el modo en vivo)
npm run build     # build de producción (carpeta dist/)
npm run lint      # ESLint
```

## Despliegue (Vercel)

Este proyecto vive en `web-react/` dentro del repo `Insight-Trader`. Al crear el proyecto en Vercel, configura **Root Directory: `web-react`**. En Vercel la app funciona en modo grabado.
