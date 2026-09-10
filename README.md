# Insight Trader - Copiloto de Trading Explicable

Sistema de agentes de IA con arquitectura RAG (fuentes internas + externas) que
genera recomendaciones de inversion (comprar/vender/mantener) justificadas en
lenguaje natural, citando los datos concretos que las respaldan.

Proyecto academico - Evaluacion "Ingenieria de Soluciones con IA" (ISY0101).
Autora: Francisca Alarcon Saldana.

## Problema que resuelve

Las fintech que ofrecen trading asistido por IA enfrentan un problema de
confianza: los clientes reciben recomendaciones sin entender por que, lo que
dificulta el cumplimiento de exigencias regulatorias de transparencia
algoritmica y reduce la adopcion de estas herramientas.

## Arquitectura

Ver diagrama y detalle de componentes en [`docs/architecture.md`](docs/architecture.md).

En resumen: un **Agente Orquestador** coordina un **Agente de Recuperacion**
(RAG con indices FAISS separados para fuentes internas y externas), un
**Agente de Analisis** (cruza perfil de riesgo del cliente con condiciones de
mercado) y un **Agente Generador** (LLM que redacta la recomendacion citando
los datos recuperados).

## Estructura del repositorio

```
src/insight_trader/
  agents/
    orchestrator.py       # Coordina el flujo completo
    retrieval_agent.py     # Consulta el pipeline RAG (fuentes internas/externas)
    analysis_agent.py      # Cruza perfil de riesgo x condiciones de mercado
    generator_agent.py     # Construye el prompt final y llama al LLM
  rag/
    retriever.py            # RAGRetriever: indices duales + recuperacion hibrida
    vector_store.py         # Vector store propio (fallback sin dependencias binarias)
    embeddings.py           # Embeddings deterministas compatibles con LangChain
  data/                      # Fuentes simuladas (mock): portafolio, transacciones,
                              # datos de mercado estilo Chainlink, noticias
  llm.py                     # Interfaz de LLM intercambiable (MockLLM / AnthropicLLM)
  main.py                    # CLI de demostracion
docs/
  architecture.md            # Diagrama de arquitectura y justificacion (IE4)
  prompts.md                 # Justificacion del diseno de prompts (IE2)
tests/                        # Pruebas automatizadas (pytest)
scripts/
  export_demo_data.py         # Exporta respuestas reales del pipeline a JSON
web/
  demo.html                   # Vista React sin build step (abrir en el navegador)
web-react/                    # App React (Vite) que consume el JSON exportado
```

## Como ejecutar

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows (Git Bash) / .venv\Scripts\activate en PowerShell
pip install -r requirements.txt
pip install -e .

# Demo por linea de comandos
python -m insight_trader.main TSLA --question "Deberia aumentar mi posicion en TSLA?"

# Pruebas automatizadas
python -m pytest -q
```

Por defecto el sistema usa `MockLLM` (sin costo, sin API key, 100% offline) para
que el pipeline completo sea reproducible en cualquier entorno de evaluacion. Para
conectar un LLM real:

```bash
export INSIGHT_TRADER_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-...
pip install anthropic
python -m insight_trader.main TSLA
```

## Vista de demostracion (React)

`web-react/` es una app React (Vite) que muestra las respuestas reales del
copiloto para las 5 posiciones del portafolio simulado, con las fuentes
citadas y la senal de riesgo-mercado. Los datos se generan ejecutando el
pipeline real (`scripts/export_demo_data.py` -> `web-react/src/data/recommendations.json`),
por lo que refleja el comportamiento efectivo del sistema, no datos inventados.
Ver [`web-react/README.md`](web-react/README.md) para instrucciones de
desarrollo y despliegue.

`web/demo.html` es una version mas simple de la misma vista (React cargado
via CDN, sin build step) util para abrir directamente en el navegador sin
instalar nada.

## Datos (simulados)

Todos los datos en `src/insight_trader/data/*.json` son simulados para fines
academicos:

- **Internas**: `clients/*.json`, un archivo por cliente simulado (portafolio,
  perfil de riesgo y historial de transacciones). Hay 3 clientes con perfiles
  de riesgo distintos: `constanza_fuentes` (moderado), `diego_herrera`
  (conservador) y `valentina_rojas` (agresivo). Usa `--client <id>` en el CLI
  para elegir uno.
- **Externas**: `market_data.json` (precios y volatilidad, simulando un feed
  tipo Chainlink Price Feeds), `news.json` (noticias financieras con sentimiento).
  Son compartidas por todos los clientes (el mercado es el mismo para todos).

## Pruebas realizadas

`tests/` contiene pruebas unitarias e integracion sobre: recuperacion correcta
por fuente y por ticker (`test_retriever.py`), logica de cruce riesgo-mercado
(`test_analysis_agent.py`) y el pipeline orquestado de extremo a extremo,
verificando que la recomendacion final cite las cifras usadas en el analisis
(`test_orchestrator.py`). Todas las pruebas corren con `MockLLM`, sin costo ni
dependencias externas.
