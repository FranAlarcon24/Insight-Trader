# Documentación técnica — Insight Trader

Este documento consolida las decisiones técnicas del proyecto, sus esquemas,
las conclusiones del desarrollo y las referencias utilizadas (IE5). Complementa
`architecture.md` (diagrama y componentes) y `prompts.md` (diseño de prompts);
aquí se explica el *por qué* de cada decisión relevante.

## 1. Justificación de decisiones de diseño

### 1.1 Arquitectura multi-agente en vez de un único LLM

Se optó por descomponer el sistema en 4 agentes con responsabilidad única
(`orchestrator.py`, `retrieval_agent.py`, `analysis_agent.py`,
`generator_agent.py`) en lugar de resolver todo con un único prompt a un LLM.

**Por qué:** un LLM consultado directamente no puede garantizar que las cifras
citadas provengan de datos reales, ni que se haya aplicado de forma
determinista la regla de negocio "si la volatilidad excede la tolerancia de
riesgo, priorizar preservación de capital". Separar la recuperación de
evidencia (agente de recuperación), el cálculo de negocio (agente de
análisis, código determinista sin LLM) y la redacción final (agente
generador) permite testear cada responsabilidad de forma aislada
(`tests/test_analysis_agent.py`, `tests/test_retriever.py`,
`tests/test_orchestrator.py`) y auditar de dónde viene cada parte de la
respuesta.

### 1.2 RAG de fuentes duales, no una sola base documental

El pipeline mantiene dos índices vectoriales separados —interno
(`portafolio`, `perfil de riesgo`, `transacciones`) y externo (`mercado`,
`noticias`)— en vez de mezclar todo en un solo índice.

**Por qué:** son fuentes con dueños, formatos y ciclos de actualización
distintos (el portafolio lo gestiona la fintech; el mercado y las noticias
vienen de terceros). Mantenerlas separadas permite que el agente de
recuperación decida explícitamente cuánta evidencia pedir a cada una, y que
el prompt final (`generator_agent.py`) las presente en secciones distinguibles
para que la recomendación pueda auditarse por origen del dato.

### 1.3 Recuperación híbrida (filtro por metadata + ranking semántico)

La primera versión del retriever usaba únicamente similitud semántica. Se
detectó en pruebas que, al usar embeddings deterministas livianos (ver 1.4),
un documento de mercado de un ticker distinto al consultado podía rankear
más alto de lo esperado, porque los documentos de mercado comparten casi todo
su vocabulario entre sí (misma plantilla de texto, solo cambian el ticker y
las cifras).

**Solución adoptada:** `RAGRetriever._filter_and_rank` primero filtra por
metadata (`ticker` exacto, o documentos generales sin ticker como el perfil
de riesgo) y solo después ordena ese subconjunto ya acotado por similitud
semántica. Esto elimina la contaminación cruzada entre activos sin perder la
capacidad de ordenar por relevancia dentro de los candidatos válidos. Es un
patrón estándar en sistemas RAG de producción (filtro duro + ranking blando).

### 1.4 Embeddings deterministas en vez de un modelo neuronal

`rag/vector_store.py` implementa `embed_text` mediante hashing de palabras en
un vector de 128 dimensiones, en vez de usar un modelo de embeddings real
(OpenAI, sentence-transformers, etc.).

**Por qué:** el proyecto debía poder ejecutarse y evaluarse sin costo, sin API
keys y sin descargar modelos, de forma reproducible en cualquier equipo
(requisito explícito de la evaluación). La interfaz `Embeddings` de LangChain
se implementó igualmente (`rag/embeddings.py`), por lo que en un entorno de
producción real basta con sustituir `DeterministicEmbeddings` por
`OpenAIEmbeddings` o `HuggingFaceEmbeddings` sin modificar `retriever.py` ni
ningún agente.

**Limitación conocida y mitigación:** ver 1.3 (recuperación híbrida).

### 1.5 LLM intercambiable (Mock por defecto, Anthropic opcional)

`llm.py` define `BaseLLM` con un único método `generate(prompt) -> str`, con
dos implementaciones: `MockLLM` (reglas deterministas sobre los datos del
prompt) y `AnthropicLLM` (llamada real a la API de Claude).

**Por qué:** permite entregar un proyecto evaluable sin costo ni credenciales,
sin sacrificar que el diseño del prompt (`generator_agent.py`,
`docs/prompts.md`) sea el mismo que se usaría con un LLM real — solo cambia
`INSIGHT_TRADER_LLM_PROVIDER=anthropic` y la variable `ANTHROPIC_API_KEY`.

### 1.6 Namespace `senal_*` en el prompt

Los campos calculados por el agente de análisis se prefijan como
`senal_volatilidad_7d_pct`, `senal_tolerancia_drawdown_pct`, etc., en vez de
usar los mismos nombres que aparecen en los chunks de contexto recuperados.

**Por qué:** durante las pruebas se detectó que, cuando el contexto recuperado
incluía cifras de otro activo mencionado incidentalmente (ej. en una
noticia), la extracción de "la cifra correcta" se volvía ambigua. Aislar las
cifras de la señal de análisis en un namespace propio elimina esa ambigüedad
tanto para `MockLLM` (que las extrae por regex) como para un LLM real (que
las puede citar sin confundirlas con datos de contexto).

### 1.7 Multi-cliente con datos internos aislados por archivo

Cada cliente simulado vive en su propio archivo
(`data/clients/<client_id>.json`) con su portafolio, perfil de riesgo y
transacciones, mientras que los datos de mercado y noticias son compartidos.

**Por qué:** refleja la realidad del dominio — el mercado es el mismo para
todos los clientes de la fintech, pero el portafolio y el perfil de riesgo son
privados por cliente. Esto también permite demostrar que la misma
recomendación de mercado produce decisiones distintas según el perfil de
riesgo (ver conclusiones, sección 3): Constanza (moderado, tolerancia 12%) y
Valentina (agresivo, tolerancia 30%) reciben recomendaciones distintas para
activos de volatilidad similar.

### 1.8 Frontend como capa de presentación, no de lógica

La vista en React (`web-react/`) consume un JSON (`recommendations.json`)
generado por una ejecución real del pipeline Python (`scripts/export_demo_data.py`)
y no reimplementa ninguna regla de negocio ni llamada a LLM.

**Por qué:** mantiene una única fuente de verdad para la lógica de agentes/RAG
(el backend Python, que es lo evaluado como pipeline de IA) y evita duplicar
o desincronizar reglas de negocio entre dos lenguajes.

## 2. Esquemas y diagramas

El diagrama de arquitectura completo (componentes, flujo de datos e
integración) está en [`architecture.md`](architecture.md). Resumen del flujo
extremo a extremo:

```
Cliente selecciona activo
        │
        ▼
RetrievalAgent ──► RAGRetriever (filtro por ticker + ranking semantico)
        │                 │
        │        ┌────────┴────────┐
        │        ▼                 ▼
        │  Indice INTERNO    Indice EXTERNO
        │  (portafolio,      (mercado tipo
        │   riesgo,           Chainlink,
        │   transacciones)    noticias)
        │
        ▼
AnalysisAgent (cruce riesgo-mercado, determinista, sin LLM)
        │
        ▼
GeneratorAgent ──► prompt con datos citados ──► LLM (Mock/Anthropic)
        │
        ▼
CopilotResponse (recomendacion + evidencia trazable)
```

El esquema de datos de un cliente simulado (`data/clients/*.json`):

```
{
  client_id, client_name,
  risk_profile: { category, max_drawdown_tolerance_pct, investment_horizon_years, notes },
  holdings: [ { ticker, name, quantity, avg_buy_price, current_weight_pct, asset_class } ],
  transactions: [ { date, ticker, action, quantity, price } ]
}
```

## 3. Conclusiones

- La separación en agentes con responsabilidad única permitió testear de
  forma aislada la lógica de negocio (cruce riesgo-mercado) sin depender de
  un LLM, lo que dio pruebas deterministas y reproducibles (9/9 en
  `pytest`).
- El principal riesgo técnico del enfoque RAG —que el LLM reciba datos del
  activo equivocado— se mitigó con recuperación híbrida (filtro por metadata
  + ranking semántico), documentada en la sección 1.3. Este hallazgo surgió
  directamente de las pruebas automatizadas, no de un análisis teórico previo.
- Diseñar las interfaces de LLM y de embeddings de forma intercambiable
  (`BaseLLM`, `Embeddings` de LangChain) permitió construir y evaluar el
  proyecto sin costo ni dependencias externas, sin comprometer que el mismo
  código sea válido para producción con un proveedor real.
- Extender el sistema a múltiples clientes con perfiles de riesgo distintos
  (moderado, conservador, agresivo) confirmó que el agente de análisis
  produce recomendaciones distintas para condiciones de mercado idénticas
  según el perfil del cliente, validando el objetivo central del caso: la
  recomendación no depende solo del activo, sino de a quién se le recomienda.
- Trabajo futuro: memoria conversacional para preguntas de seguimiento;
  métricas de portafolio agregado (correlación entre posiciones, no solo
  análisis activo por activo); reemplazo de los embeddings deterministas por
  un modelo neuronal en un despliegue de producción.

## 4. Referencias (formato APA)

Anthropic. (2024). *Claude API documentation*. https://docs.anthropic.com/

Chainlink Labs. (2024). *Chainlink Price Feeds documentation*. https://docs.chain.link/data-feeds

Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search
with GPUs. *IEEE Transactions on Big Data*. https://doi.org/10.1109/TBDATA.2019.2921572

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N.,
Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D.
(2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. En
H. Larochelle, M. Ranzato, R. Hadsell, M. F. Balcan, & H. Lin (Eds.),
*Advances in Neural Information Processing Systems* (Vol. 33, pp. 9459–9474).
Curran Associates.

LangChain. (2024). *LangChain documentation*. https://python.langchain.com/

Vite. (2024). *Vite documentation*. https://vitejs.dev/
