# Insight Trader — Vista en React

Frontend de visualizacion para el copiloto de trading explicable. Es una capa
de presentacion sobre el pipeline Python (agentes + RAG): no reimplementa
ninguna logica de negocio, solo muestra las respuestas que ya genero el
backend.

## Como funciona

Los datos vienen de `src/data/recommendations.json`, un archivo generado por
el backend Python ejecutando el pipeline real para cada posicion del
portafolio simulado (ver `../scripts/export_demo_data.py`). El componente
`App.jsx` importa ese JSON y renderiza:

- `Sidebar`: lista de posiciones del portafolio (clic para seleccionar ticker).
- `SignalPills`: perfil de riesgo, volatilidad, cambio, tendencia y sentimiento
  del activo seleccionado.
- `SourceColumn` (x2): los chunks citados de las fuentes internas y externas
  recuperadas por el pipeline RAG.
- `RecommendationCard`: la recomendacion final generada por el LLM.

## Regenerar los datos

Si cambias los datos simulados del backend (`src/insight_trader/data/*.json`)
y quieres reflejarlo aqui:

```bash
cd ..
source .venv/Scripts/activate
python scripts/export_demo_data.py
cp recommendations.json web-react/src/data/recommendations.json
rm recommendations.json
```

## Desarrollo

```bash
npm install
npm run dev       # servidor de desarrollo
npm run build     # build de produccion (carpeta dist/)
npm run lint      # ESLint
```

## Despliegue (Vercel)

Este proyecto vive en `web-react/` dentro del repo `Insight-Trader`. Al crear
el proyecto en Vercel, configura **Root Directory: `web-react`** para que
despliegue solo esta carpeta.
