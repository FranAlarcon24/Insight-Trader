# Insight Trader: Copiloto de Trading Explicable
### Informe tecnico de propuesta e implementacion

**Autora:** Francisca Alarcon Saldana
**Asignatura:** ISY0101 - Ingenieria de Soluciones con IA
**Evaluacion:** Diseno e implementacion de solucion con agentes de IA

---

## 1. Analisis del caso organizacional

**Organizacion:** Fintech de inversion asistida por IA (caso representativo del
sector, con preferencia por un contexto real de la industria de wealthtech
retail y boutique).

**Rubro y contexto:** Servicios financieros digitales (fintech), segmento de
herramientas de inversion asistida por inteligencia artificial dirigidas a
inversionistas retail y gestores de fondos boutique.

**Problema:** Los clientes de este tipo de fintech reciben recomendaciones de
trading (comprar, vender, mantener) generadas por modelos de IA, pero sin
entender *por que* el sistema sugiere esa accion. Esta falta de trazabilidad
genera tres impactos concretos:

1. **Desconfianza del cliente**, que reduce la adopcion y retencion del
   producto.
2. **Riesgo de incumplimiento regulatorio**, ya que las normativas de
   transparencia algoritmica en servicios financieros (ej. requisitos de
   explicabilidad de modelos que afectan decisiones de inversion) exigen poder
   justificar una recomendacion ante clientes y auditores.
3. **Barrera de adopcion en segmentos profesionales**, ya que gestores de
   fondos boutique necesitan poder defender cada decision ante sus propios
   clientes finales.

**Objetivos de la intervencion:**

- O1: Generar recomendaciones de trading (comprar/vender/mantener) que citen
  explicitamente los datos concretos (cifras de mercado, perfil de riesgo) que
  las respaldan.
- O2: Cruzar automaticamente el perfil de riesgo declarado por el cliente con
  las condiciones de mercado vigentes del activo consultado, antes de emitir
  una recomendacion.
- O3: Mantener una arquitectura auditable, donde cada respuesta pueda
  trazarse hasta las fuentes de datos (internas y externas) que la originaron.

**Datos disponibles o simulados:** Para esta evaluacion se simulan los cuatro
insumos de datos que la fintech ya posee o puede obtener via integraciones: (a)
portafolio y perfil de riesgo del cliente, (b) historial de transacciones, (c)
datos de mercado en tiempo real (con formato analogo a un oraculo de precios
tipo Chainlink Price Feeds) y (d) noticias financieras con sentimiento. Los
archivos JSON de datos simulados estan en `src/insight_trader/data/`.

**Restricciones y requerimientos particulares:**

- El sistema no debe inventar cifras: toda afirmacion numerica en la
  recomendacion debe provenir de datos efectivamente recuperados (requisito de
  explicabilidad/transparencia algoritmica).
- La recomendacion debe respetar el perfil de riesgo declarado por el cliente
  (regla de negocio: si la volatilidad del activo excede la tolerancia de
  drawdown del cliente, se debe priorizar preservacion de capital).
- La solucion debe ser reproducible sin costo de API para fines de evaluacion
  academica (se implemento con un LLM simulado por defecto, con interfaz
  intercambiable a un proveedor real).

**Motivacion para el uso de agentes de IA, LLMs y RAG:** Un unico LLM
consultado directamente sobre el portafolio del cliente no puede garantizar
que las cifras citadas sean reales ni que se hayan considerado ambas fuentes de
informacion (interna y externa) de forma sistematica. Una arquitectura de
agentes con RAG permite: (1) separar la recuperacion de evidencia verificable
de la generacion de lenguaje natural, (2) aplicar logica de negocio
determinista (cruce riesgo-mercado) de forma confiable antes de la generacion,
y (3) mantener trazabilidad de cada fuente citada, condiciones necesarias para
cumplir los objetivos O1-O3.

---

## 2. Formulacion de prompts

El diseno de prompts se detalla extensamente en [`docs/prompts.md`](prompts.md).
En sintesis, el prompt del Agente Generador:

1. Fija el rol del sistema y una restriccion explicita anti-alucinacion
   ("Nunca inventes cifras: usa solo los datos entregados abajo"), directamente
   alineada con el requerimiento regulatorio de transparencia algoritmica.
2. Separa visualmente el contexto interno del externo, para permitir auditar
   el origen de cada dato citado.
3. Aisla las cifras calculadas por el Agente de Analisis en un namespace propio
   (`senal_*`) para evitar ambiguedad cuando el contexto recuperado contiene
   multiples cifras similares.
4. Enumera instrucciones de salida verificables: recomendacion clara de tres
   opciones, cita obligatoria de al menos una cifra concreta, y una regla de
   negocio condicional que traduce el perfil de riesgo del cliente en una
   restriccion de generacion.

Las consultas de recuperacion tambien se formulan de forma diferenciada segun
la fuente (vocabulario de portafolio/riesgo vs. vocabulario de mercado/noticias)
y se combinan con un filtro obligatorio por ticker, decision que se tomo tras
detectar en las pruebas que el embedding liviano por si solo no discriminaba
con precision suficiente entre activos de vocabulario similar (ver seccion 5).

---

## 3. Diseno e implementacion del pipeline RAG

El pipeline RAG (`src/insight_trader/rag/`) integra dos fuentes de datos en
indices vectoriales independientes, construidos con **FAISS** a traves de
**LangChain**:

- **Indice interno**: documentos generados a partir de `portfolio.json`
  (perfil de riesgo y posiciones) y `transactions.json` (historial), con
  metadata `{type, ticker}` por documento.
- **Indice externo**: documentos generados a partir de `market_data.json`
  (precios y volatilidad estilo Chainlink) y `news.json` (noticias con
  sentimiento), con la misma metadata.

**Flujo de recuperacion (hibrido):**

1. El `RetrievalAgent` recibe `(ticker, pregunta)` y construye una consulta
   textual por fuente.
2. `RAGRetriever._filter_and_rank` primero **filtra por metadata** (documentos
   cuyo `ticker` coincide con el consultado, o documentos generales sin ticker
   como el perfil de riesgo), y luego **ordena por similitud semantica** dentro
   de ese subconjunto ya acotado.
3. El resultado son *chunks* citables (oraciones autocontenidas con cifras),
   que se pasan intactos al Agente Generador junto con la senal del Agente de
   Analisis.

**Decision tecnica documentada:** los embeddings usados (`rag/embeddings.py`,
`rag/vector_store.py`) son deterministas (hashing de palabras) en vez de un
modelo neuronal, para que el pipeline sea 100% offline, gratuito y
reproducible en cualquier entorno de evaluacion, sin depender de descargas de
modelos ni API keys. Esta eleccion tiene una limitacion conocida -baja
capacidad de discriminacion semantica fina entre documentos con vocabulario muy
similar-, que se mitiga con el filtro por metadata descrito arriba. La interfaz
de `Embeddings` de LangChain se respeta integramente, por lo que en produccion
basta con sustituir `DeterministicEmbeddings` por `OpenAIEmbeddings` o
`HuggingFaceEmbeddings` sin modificar el resto del pipeline.

---

## 4. Arquitectura de la solucion

Ver diagrama completo en [`docs/architecture.md`](architecture.md).

```
Pregunta del cliente
        |
        v
Agente Orquestador (TradingCopilotOrchestrator)
        |
        +--> Agente de Recuperacion --> RAG dual (FAISS interno / FAISS externo)
        |                                       |
        |                          Fuentes internas: portafolio, riesgo, transacciones
        |                          Fuentes externas: mercado (Chainlink-like), noticias
        |
        +--> Agente de Analisis --> cruza perfil de riesgo x condiciones de mercado
        |
        +--> Agente Generador --> prompt con datos citados --> LLM (Mock / Anthropic)
        |
        v
Respuesta: recomendacion + justificacion + fuentes citadas
```

Los cuatro componentes (orquestador, recuperacion, analisis, generacion) estan
implementados como clases independientes con responsabilidad unica, comunicadas
mediante estructuras de datos tipadas (`RetrievedChunk`, `RiskMarketSignal`,
`CopilotResponse`), lo que permite testear cada agente de forma aislada (ver
seccion 5) y reemplazar cualquier componente (ej. el LLM o el vector store) sin
modificar los demas.

---

## 5. Documentacion tecnica: pruebas y conclusiones

**Pruebas automatizadas** (`tests/`, ejecutadas con `pytest`, 9/9 exitosas):

- `test_retriever.py`: valida que la recuperacion interna y externa devuelva
  resultados relevantes al ticker consultado.
- `test_analysis_agent.py`: valida que el cruce riesgo-mercado marque
  correctamente activos cuya volatilidad excede la tolerancia del cliente (ej.
  ETH, volatilidad 24.6% > tolerancia 12%) y no marque activos estables (ej.
  BND, volatilidad 1.2%).
- `test_orchestrator.py`: valida el pipeline de extremo a extremo, incluyendo
  que la recomendacion final cite el numero exacto de volatilidad usado en el
  analisis (trazabilidad numerica) y que las fuentes internas/externas queden
  correctamente etiquetadas en la respuesta.

**Hallazgo relevante durante las pruebas:** la primera version del retriever
(busqueda semantica pura, sin filtro por ticker) recuperaba ocasionalmente
datos de mercado de un activo distinto al consultado, debido a la baja
capacidad discriminativa del embedding liviano ante documentos con vocabulario
casi identico. Se corrigio implementando la recuperacion hibrida
(filtro por metadata + ranking semantico) descrita en la seccion 3, quedando
documentada como decision de diseno en `docs/prompts.md`.

**Conclusiones:**

- La combinacion de agentes especializados + RAG de fuentes duales permite
  cumplir el objetivo central del caso: recomendaciones auditables, con cifras
  verificables y alineadas al perfil de riesgo del cliente.
- La arquitectura modular (interfaces intercambiables para LLM y vector store)
  permite migrar de una implementacion offline/sin costo (usada en esta
  evaluacion) a un proveedor LLM real (Anthropic) y a embeddings neuronales en
  produccion, sin rediseno del pipeline.
- Trabajo futuro: incorporar memoria conversacional para preguntas de
  seguimiento, y ampliar el Agente de Analisis con metricas de portafolio
  agregado (ej. correlacion entre posiciones) mas alla del analisis
  activo-por-activo actual.

---

## Referencias

- Lewis, P., Perez, E., Piktus, A., et al. (2020). *Retrieval-Augmented
  Generation for Knowledge-Intensive NLP Tasks*. Advances in Neural
  Information Processing Systems, 33.
- Johnson, J., Douze, M., & Jegou, H. (2019). *Billion-scale similarity search
  with GPUs*. IEEE Transactions on Big Data. (FAISS)
- LangChain. (2024). *LangChain Documentation*. https://python.langchain.com/
- Chainlink Labs. (2024). *Chainlink Price Feeds Documentation*.
  https://docs.chain.link/data-feeds
- Anthropic. (2024). *Claude API Documentation*. https://docs.anthropic.com/
