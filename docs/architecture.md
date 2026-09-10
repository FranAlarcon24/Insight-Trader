# Arquitectura de la solucion

## Diagrama de componentes

```mermaid
flowchart TB
    subgraph Cliente["Cliente de la fintech"]
        Q["Pregunta en lenguaje natural\nej. Deberia mantener mi posicion en TSLA?"]
    end

    subgraph Orquestador["Agente Orquestador (TradingCopilotOrchestrator)"]
        direction TB
        O1["1. Recibe ticker + pregunta"]
        O2["4. Ensambla respuesta final"]
    end

    subgraph Agentes["Agentes especializados"]
        RA["Agente de Recuperacion\n(RetrievalAgent)"]
        AA["Agente de Analisis\n(AnalysisAgent)\ncruza perfil de riesgo x mercado"]
        GA["Agente Generador\n(GeneratorAgent + LLM)"]
    end

    subgraph RAG["Pipeline RAG - fuentes duales"]
        direction TB
        VS_INT["Indice vectorial INTERNO\n(FAISS via LangChain)"]
        VS_EXT["Indice vectorial EXTERNO\n(FAISS via LangChain)"]
    end

    subgraph FuentesInt["Fuentes internas (fintech)"]
        P["Portafolio del cliente"]
        RP["Perfil de riesgo"]
        TX["Historial de transacciones"]
    end

    subgraph FuentesExt["Fuentes externas"]
        MK["Datos de mercado en tiempo real\n(estilo Chainlink Price Feeds)"]
        NW["Noticias financieras relevantes"]
    end

    LLM["LLM\n(interfaz intercambiable:\nMockLLM offline / AnthropicLLM real)"]

    Q --> O1
    O1 --> RA
    RA -->|consulta con filtro por ticker| VS_INT
    RA -->|consulta con filtro por ticker| VS_EXT
    P --> VS_INT
    RP --> VS_INT
    TX --> VS_INT
    MK --> VS_EXT
    NW --> VS_EXT
    RA --> AA
    O1 --> AA
    AA -->|senal de riesgo-mercado estructurada| GA
    RA -->|chunks citables| GA
    GA -->|prompt con datos citados| LLM
    LLM -->|recomendacion + justificacion| GA
    GA --> O2
    O2 --> Resp["Respuesta al cliente:\nrecomendacion + fuentes citadas"]
```

## Componentes clave y su integracion

1. **Agente Orquestador** (`insight_trader/agents/orchestrator.py`): punto de entrada unico. Recibe `(ticker, pregunta)`, coordina la secuencia recuperacion -> analisis -> generacion, y devuelve un objeto `CopilotResponse` con la recomendacion y toda la evidencia usada (trazabilidad).

2. **Agente de Recuperacion** (`retrieval_agent.py`): construye las consultas para el pipeline RAG y obtiene chunks relevantes de ambas fuentes (interna y externa), filtrando siempre por el ticker consultado para evitar contaminacion cruzada entre activos.

3. **Pipeline RAG de fuentes duales** (`rag/retriever.py`, `rag/vector_store.py`, `rag/embeddings.py`): dos indices vectoriales independientes (interno/externo) construidos con FAISS a traves de LangChain. La recuperacion es hibrida: filtra candidatos por metadata (ticker) y luego ordena por similitud semantica, evitando que el LLM reciba datos de un activo distinto al consultado.

4. **Agente de Analisis** (`analysis_agent.py`): logica determinista que cruza el perfil de riesgo del cliente (tolerancia a drawdown) con las condiciones de mercado del activo (volatilidad, tendencia) y el sentimiento de noticias, produciendo una senal estructurada (`RiskMarketSignal`).

5. **Agente Generador** (`generator_agent.py`): ensambla el prompt final (ver `docs/prompts.md`) combinando los chunks recuperados y la senal de analisis, y delega la redaccion de la recomendacion en lenguaje natural al LLM.

6. **Interfaz de LLM intercambiable** (`llm.py`): `MockLLM` (offline, determinista, usada en las pruebas de esta entrega) y `AnthropicLLM` (real, activable con `INSIGHT_TRADER_LLM_PROVIDER=anthropic` y `ANTHROPIC_API_KEY`), ambas implementando el mismo contrato `generate(prompt) -> str`.

## Flujo de datos (resumen)

`Pregunta del cliente -> Orquestador -> Recuperacion (RAG dual) -> Analisis (riesgo x mercado) -> Generacion (LLM con datos citados) -> Respuesta explicable`
