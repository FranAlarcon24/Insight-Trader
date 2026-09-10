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
algoritmica y reduce la adopcion de estas herramientas. Ver `docs/informe.md`
para el analisis completo del caso.

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
  informe.md                 # Informe tecnico de la evaluacion (max. 5 paginas)
tests/                        # Pruebas automatizadas (pytest)
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

`web/demo.html` es una vista independiente en React (sin build step, cargada
via CDN) que muestra las respuestas reales del copiloto para las 5 posiciones
del portafolio simulado, con las fuentes citadas y la senal de riesgo-mercado.
Se genero capturando la salida real del pipeline (`orchestrator.ask(...)`) para
cada ticker, por lo que refleja el comportamiento efectivo del sistema, no datos
inventados. Para verla, abre el archivo directamente en un navegador.

## Datos (simulados)

Todos los datos en `src/insight_trader/data/*.json` son simulados para fines
academicos:

- **Internas**: `portfolio.json` (portafolio + perfil de riesgo del cliente),
  `transactions.json` (historial de transacciones).
- **Externas**: `market_data.json` (precios y volatilidad, simulando un feed
  tipo Chainlink Price Feeds), `news.json` (noticias financieras con sentimiento).

## Pruebas realizadas

`tests/` contiene pruebas unitarias e integracion sobre: recuperacion correcta
por fuente y por ticker (`test_retriever.py`), logica de cruce riesgo-mercado
(`test_analysis_agent.py`) y el pipeline orquestado de extremo a extremo,
verificando que la recomendacion final cite las cifras usadas en el analisis
(`test_orchestrator.py`). Todas las pruebas corren con `MockLLM`, sin costo ni
dependencias externas.
