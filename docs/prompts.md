# Formulacion y justificacion de prompts

## Prompt del Agente Generador (`insight_trader/agents/generator_agent.py`)

El prompt es la pieza central de explicabilidad del sistema, por lo que su diseno
responde directamente al problema planteado (desconfianza por falta de
trazabilidad). Decisiones de diseno:

1. **Rol y restriccion anti-alucinacion explicitas.** La primera linea fija el rol
   ("copiloto de trading explicable") y una instruccion dura: *"Nunca inventes
   cifras: usa solo los datos entregados abajo"*. Esto reduce el riesgo de que el
   LLM invente numeros de mercado no verificados, un requisito regulatorio
   (transparencia algoritmica) mencionado en el planteamiento del problema.

2. **Separacion visual de fuentes (interna vs externa).** El prompt usa
   delimitadores (`--- Contexto interno ---`, `--- Contexto externo ---`) para que
   el modelo distinga el origen de cada dato, lo que permite auditar despues cual
   fuente sustento cada parte de la recomendacion.

3. **Seccion de senal estructurada con namespace propio (`senal_*`).** Los
   campos calculados por el Agente de Analisis (`senal_volatilidad_7d_pct`,
   `senal_tolerancia_drawdown_pct`, etc.) se prefijan deliberadamente para que no
   colisionen textualmente con cifras que puedan aparecer en los chunks de
   contexto recuperados (ej. la volatilidad de otro activo mencionado de forma
   incidental en una noticia). Esto se detecto durante las pruebas: sin el
   prefijo, la extraccion de la cifra "correcta" era ambigua cuando el contexto
   contenia varios numeros con la misma etiqueta.

4. **Instrucciones de salida enumeradas y verificables.** Se pide explicitamente
   (a) una recomendacion clara de tres opciones (comprar/vender/mantener), (b) al
   menos una cifra concreta citada de la seccion de senal, y (c) una regla de
   negocio condicional ("si excede la tolerancia de riesgo, priorizar
   preservacion de capital"). Esta ultima instruccion traduce una politica de
   negocio (perfil de riesgo del cliente) en una restriccion de generacion,
   evitando que el modelo optimice solo por retorno esperado.

5. **Formato citable por diseno.** Como cada chunk de contexto es una oracion
   autocontenida con cifras (ej. "volatilidad_7d_pct: 21.8"), el LLM puede citar
   literalmente la evidencia en su justificacion, cumpliendo el objetivo de la
   propuesta: *"citando los datos concretos que la respaldan"*.

## Prompts de las consultas de recuperacion (`insight_trader/agents/retrieval_agent.py`)

Las consultas al indice interno y externo se construyen de forma distinta porque
apuntan a vocabularios distintos:

- Consulta interna: `"{ticker} {pregunta} perfil de riesgo posicion transacciones"`
  prioriza terminos que aparecen en los documentos de portafolio/riesgo/historial.
- Consulta externa: `"{ticker} {pregunta} precio volatilidad tendencia noticias"`
  prioriza terminos de mercado y noticias.

Ambas consultas se combinan ademas con un **filtro obligatorio por ticker** (ver
`RAGRetriever._filter_and_rank`) antes del ranking semantico. Esta decision se
tomo tras observar en pruebas que el embedding liviano (ver justificacion tecnica
en `rag/vector_store.py`) por si solo no discriminaba con suficiente precision
entre activos con vocabulario muy similar (ej. dos filas de datos de mercado que
comparten casi toda su redaccion salvo el ticker y las cifras). El filtro por
metadata garantiza precision; el ranking semantico decide el orden dentro de los
candidatos ya validos.
