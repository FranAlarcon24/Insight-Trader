# Evidencia de toma de decisiones del agente

Generado automaticamente con `python scripts/demo_escenarios.py` (LLM simulado, determinista). Las reglas R0-R6 estan definidas en `src/insight_trader/agent/planner.py` y descritas en `docs/architecture.md`.

## Escenario 1 - Misma pregunta, distinto perfil de riesgo

Mismo activo y mismo mercado; cambia solo el cliente (moderado, tolerancia 12% vs agresivo, 30%).

**Cliente:** `constanza_fuentes` | **Pregunta:** "Que hago con TSLA?"

Herramientas ejecutadas:

```
1. consultar_portafolio({"ticker": "TSLA"})
2. recordar_memoria({"consulta": "Que hago con TSLA?", "ticker": "TSLA"})
3. consultar_mercado({"ticker": "TSLA"})
4. evaluar_riesgo({"ticker": "TSLA"})
5. registrar_alerta({"ticker": "TSLA", "severidad": "alta", "motivo": "volatilidad 21.8% supera tolerancia 12% del cliente"})
6. buscar_noticias({"ticker": "TSLA"})
7. evaluar_concentracion({})
8. registrar_alerta({"ticker": "PORTAFOLIO", "severidad": "media", "motivo": "exposicion a equity_tech 40.5% supera el limite 40.0% del perfil moderado"})
9. generar_informe({"ticker": "TSLA", "recomendacion": "reducir posicion", "justificacion": "la volatilidad a 7 dias (21.8%) supera la tolerancia del cliente (12%) por 9.8 puntos; ademas el portafolio tiene 40.5% en equity_tech (limite 40.0% para perfil moderado)."})
```

Decisiones de re-planificacion:

- R3 riesgo: TSLA excede tolerancia (21.8% > 12%) -> se agrega T7 registrar_alerta (P1, severidad alta)
- R3 riesgo: se agrega T8 evaluar_concentracion (P3) para dimensionar cuanto reducir
- R5 concentracion: equity_tech pesa 40.5% (> 40.0%) -> se agrega T9 registrar_alerta (P2)

Plan final:

```
T1 [completada] P1 consultar_portafolio({"ticker": "TSLA"}) - Validar que el cliente tiene posicion en el activo antes de analizar
T2 [completada] P1 recordar_memoria({"consulta": "Que hago con TSLA?", "ticker": "TSLA"}) - Recuperar recomendaciones previas y preferencias del cliente
T3 [completada] P1 consultar_mercado({"ticker": "TSLA"}) - Obtener precio, volatilidad y frescura del dato
T7 [completada] P1 registrar_alerta({"ticker": "TSLA", "severidad": "alta", "motivo": "volatilidad 21.8% supera tolerancia 12% del cliente"}) - Riesgo sobre la tolerancia: se notifica al asesor antes de seguir
T4 [completada] P2 evaluar_riesgo({"ticker": "TSLA"}) - Cruzar volatilidad del activo con la tolerancia del cliente
T9 [completada] P2 registrar_alerta({"ticker": "PORTAFOLIO", "severidad": "media", "motivo": "exposicion a equity_tech 40.5% supera el limite 40.0% del perfil moderado"}) - Concentracion por sobre el limite del perfil
T5 [completada] P3 buscar_noticias({"ticker": "TSLA"}) - Complementar con sentimiento de noticias recientes
T8 [completada] P3 evaluar_concentracion({}) - Medir el impacto del activo riesgoso en la exposicion total
T6 [completada] P4 generar_informe({"ticker": "TSLA"}) - Dejar registro escrito y trazable de la recomendacion
```

Respuesta:

> Recomendacion para TSLA: reducir posicion.
> Justificacion: la volatilidad a 7 dias (21.8%) supera la tolerancia del cliente (12%) por 9.8 puntos; ademas el portafolio tiene 40.5% en equity_tech (limite 40.0% para perfil moderado).
> Alertas registradas para tu asesor: [alta] TSLA: volatilidad 21.8% supera tolerancia 12% del cliente; [media] PORTAFOLIO: exposicion a equity_tech 40.5% supera el limite 40.0% del perfil moderado

**Cliente:** `valentina_rojas` | **Pregunta:** "Que hago con TSLA?"

Herramientas ejecutadas:

```
1. consultar_portafolio({"ticker": "TSLA"})
2. recordar_memoria({"consulta": "Que hago con TSLA?", "ticker": "TSLA"})
3. consultar_mercado({"ticker": "TSLA"})
4. evaluar_riesgo({"ticker": "TSLA"})
5. buscar_noticias({"ticker": "TSLA"})
6. generar_informe({"ticker": "TSLA", "recomendacion": "mantener posicion", "justificacion": "tendencia positiva (12.4% en 7 dias) con noticias positivas y volatilidad (21.8%) dentro de la tolerancia (30%)."})
```

Plan final:

```
T1 [completada] P1 consultar_portafolio({"ticker": "TSLA"}) - Validar que el cliente tiene posicion en el activo antes de analizar
T2 [completada] P1 recordar_memoria({"consulta": "Que hago con TSLA?", "ticker": "TSLA"}) - Recuperar recomendaciones previas y preferencias del cliente
T3 [completada] P1 consultar_mercado({"ticker": "TSLA"}) - Obtener precio, volatilidad y frescura del dato
T4 [completada] P2 evaluar_riesgo({"ticker": "TSLA"}) - Cruzar volatilidad del activo con la tolerancia del cliente
T5 [completada] P3 buscar_noticias({"ticker": "TSLA"}) - Complementar con sentimiento de noticias recientes
T6 [completada] P4 generar_informe({"ticker": "TSLA"}) - Dejar registro escrito y trazable de la recomendacion
```

Respuesta:

> Recomendacion para TSLA: mantener posicion.
> Justificacion: tendencia positiva (12.4% en 7 dias) con noticias positivas y volatilidad (21.8%) dentro de la tolerancia (30%).

## Escenario 2 - Condicion cambiante: shock de mercado en mitad de la conversacion

Misma conversacion (thread_id). Entre turnos el entorno pasa de `normal` a `shock`. La segunda pregunta no menciona el activo: se hereda de la memoria de corto plazo, y la memoria de largo plazo aporta la recomendacion anterior para explicar el cambio.

**Cliente:** `valentina_rojas` | **Pregunta:** "Que hago con TSLA?"

Herramientas ejecutadas:

```
1. consultar_portafolio({"ticker": "TSLA"})
2. recordar_memoria({"consulta": "Que hago con TSLA?", "ticker": "TSLA"})
3. consultar_mercado({"ticker": "TSLA"})
4. evaluar_riesgo({"ticker": "TSLA"})
5. buscar_noticias({"ticker": "TSLA"})
6. generar_informe({"ticker": "TSLA", "recomendacion": "mantener posicion", "justificacion": "tendencia positiva (12.4% en 7 dias) con noticias positivas y volatilidad (21.8%) dentro de la tolerancia (30%)."})
```

Plan final:

```
T1 [completada] P1 consultar_portafolio({"ticker": "TSLA"}) - Validar que el cliente tiene posicion en el activo antes de analizar
T2 [completada] P1 recordar_memoria({"consulta": "Que hago con TSLA?", "ticker": "TSLA"}) - Recuperar recomendaciones previas y preferencias del cliente
T3 [completada] P1 consultar_mercado({"ticker": "TSLA"}) - Obtener precio, volatilidad y frescura del dato
T4 [completada] P2 evaluar_riesgo({"ticker": "TSLA"}) - Cruzar volatilidad del activo con la tolerancia del cliente
T5 [completada] P3 buscar_noticias({"ticker": "TSLA"}) - Complementar con sentimiento de noticias recientes
T6 [completada] P4 generar_informe({"ticker": "TSLA"}) - Dejar registro escrito y trazable de la recomendacion
```

Respuesta:

> Recomendacion para TSLA: mantener posicion.
> Justificacion: tendencia positiva (12.4% en 7 dias) con noticias positivas y volatilidad (21.8%) dentro de la tolerancia (30%).

**Cliente:** `valentina_rojas` | **Pregunta:** "Y ahora, con la caida del mercado?"

Herramientas ejecutadas:

```
1. consultar_portafolio({"ticker": "TSLA"})
2. recordar_memoria({"consulta": "Y ahora, con la caida del mercado?", "ticker": "TSLA"})
3. consultar_mercado({"ticker": "TSLA"})
4. evaluar_riesgo({"ticker": "TSLA"})
5. registrar_alerta({"ticker": "TSLA", "severidad": "critica", "motivo": "volatilidad 39.2% supera tolerancia 30% del cliente"})
6. buscar_noticias({"ticker": "TSLA"})
7. evaluar_concentracion({})
8. generar_informe({"ticker": "TSLA", "recomendacion": "reducir posicion", "justificacion": "la volatilidad a 7 dias (39.2%) supera la tolerancia del cliente (30%) por 9.2 puntos; el precio cae -16.9% en 7 dias con sentimiento negativo; esto CAMBIA la recomendacion anterior ('mantener posicion', 2026-10-22T21:53:32) porque las condiciones observadas son distintas."})
```

Decisiones de re-planificacion:

- R0 contexto: la pregunta no menciona un activo -> se usa TSLA del turno anterior (memoria de corto plazo)
- R2 memoria: existe recomendacion previa para TSLA (2026-10-22T21:53:32): la respuesta debe indicar si la decision cambia y por que
- R3 riesgo: TSLA excede tolerancia (39.2% > 30%) -> se agrega T7 registrar_alerta (P1, severidad critica)
- R3 riesgo: se agrega T8 evaluar_concentracion (P3) para dimensionar cuanto reducir

Plan final:

```
T1 [completada] P1 consultar_portafolio({"ticker": "TSLA"}) - Validar que el cliente tiene posicion en el activo antes de analizar
T2 [completada] P1 recordar_memoria({"consulta": "Y ahora, con la caida del mercado?", "ticker": "TSLA"}) - Recuperar recomendaciones previas y preferencias del cliente
T3 [completada] P1 consultar_mercado({"ticker": "TSLA"}) - Obtener precio, volatilidad y frescura del dato
T7 [completada] P1 registrar_alerta({"ticker": "TSLA", "severidad": "critica", "motivo": "volatilidad 39.2% supera tolerancia 30% del cliente"}) - Riesgo sobre la tolerancia: se notifica al asesor antes de seguir
T4 [completada] P2 evaluar_riesgo({"ticker": "TSLA"}) - Cruzar volatilidad del activo con la tolerancia del cliente
T5 [completada] P3 buscar_noticias({"ticker": "TSLA"}) - Complementar con sentimiento de noticias recientes
T8 [completada] P3 evaluar_concentracion({}) - Medir el impacto del activo riesgoso en la exposicion total
T6 [completada] P4 generar_informe({"ticker": "TSLA"}) - Dejar registro escrito y trazable de la recomendacion
```

Respuesta:

> Recomendacion para TSLA: reducir posicion.
> Justificacion: la volatilidad a 7 dias (39.2%) supera la tolerancia del cliente (30%) por 9.2 puntos; el precio cae -16.9% en 7 dias con sentimiento negativo; esto CAMBIA la recomendacion anterior ('mantener posicion', 2026-10-22T21:53:32) porque las condiciones observadas son distintas.
> Alertas registradas para tu asesor: [critica] TSLA: volatilidad 39.2% supera tolerancia 30% del cliente

## Escenario 3 - Datos de mercado desactualizados

El feed de precios dejo de actualizarse hace 72 h. El agente cancela tareas que dependen del dato y se niega a recomendar operar.

**Cliente:** `diego_herrera` | **Pregunta:** "Que hago con BND?"

Herramientas ejecutadas:

```
1. consultar_portafolio({"ticker": "BND"})
2. recordar_memoria({"consulta": "Que hago con BND?", "ticker": "BND"})
3. consultar_mercado({"ticker": "BND"})
4. registrar_alerta({"ticker": "BND", "severidad": "media", "motivo": "feed de mercado con 72.0 h de antiguedad"})
5. generar_informe({"ticker": "BND", "recomendacion": "no operar: mantener la posicion sin cambios hasta contar con datos actualizados", "justificacion": "el feed de mercado tiene 72.0 h de antiguedad (limite 24 h), por lo que cualquier decision se basaria en precios que ya no son reales."})
```

Decisiones de re-planificacion:

- R4 datos: el feed tiene 72.0 h (> 24 h) -> se cancelan T4, T5 y se agrega T7 registrar_alerta; la recomendacion queda en 'no operar'

Plan final:

```
T1 [completada] P1 consultar_portafolio({"ticker": "BND"}) - Validar que el cliente tiene posicion en el activo antes de analizar
T2 [completada] P1 recordar_memoria({"consulta": "Que hago con BND?", "ticker": "BND"}) - Recuperar recomendaciones previas y preferencias del cliente
T3 [completada] P1 consultar_mercado({"ticker": "BND"}) - Obtener precio, volatilidad y frescura del dato
T7 [completada] P1 registrar_alerta({"ticker": "BND", "severidad": "media", "motivo": "feed de mercado con 72.0 h de antiguedad"}) - No se puede recomendar con datos viejos: se avisa al asesor
T4 [cancelada] P2 evaluar_riesgo({"ticker": "BND"}) - Cruzar volatilidad del activo con la tolerancia del cliente | cancelada: datos de mercado desactualizados
T5 [cancelada] P3 buscar_noticias({"ticker": "BND"}) - Complementar con sentimiento de noticias recientes | cancelada: datos de mercado desactualizados
T6 [completada] P4 generar_informe({"ticker": "BND"}) - Dejar registro escrito y trazable de la recomendacion
```

Respuesta:

> Recomendacion para BND: no operar: mantener la posicion sin cambios hasta contar con datos actualizados.
> Justificacion: el feed de mercado tiene 72.0 h de antiguedad (limite 24 h), por lo que cualquier decision se basaria en precios que ya no son reales.
> Alertas registradas para tu asesor: [media] BND: feed de mercado con 72.0 h de antiguedad

## Escenario 4 - Memoria de largo plazo entre sesiones

En una sesion previa la cliente dijo: "Recuerda que no quiero aumentar mi exposicion a cripto" (guardado con `guardar_preferencia`). Se crea una instancia NUEVA del agente con la misma base SQLite y se pregunta por ETH.

**Cliente:** `constanza_fuentes` | **Pregunta:** "Que hago con ETH?"

Herramientas ejecutadas:

```
1. consultar_portafolio({"ticker": "ETH"})
2. recordar_memoria({"consulta": "Que hago con ETH?", "ticker": "ETH"})
3. consultar_mercado({"ticker": "ETH"})
4. evaluar_riesgo({"ticker": "ETH"})
5. registrar_alerta({"ticker": "ETH", "severidad": "alta", "motivo": "volatilidad 24.6% supera tolerancia 12% del cliente"})
6. buscar_noticias({"ticker": "ETH"})
7. evaluar_concentracion({})
8. registrar_alerta({"ticker": "PORTAFOLIO", "severidad": "media", "motivo": "exposicion a equity_tech 40.5% supera el limite 40.0% del perfil moderado"})
9. generar_informe({"ticker": "ETH", "recomendacion": "reducir posicion", "justificacion": "la volatilidad a 7 dias (24.6%) supera la tolerancia del cliente (12%) por 12.6 puntos; se respeta la preferencia registrada del cliente: \"Recuerda que no quiero aumentar mi exposicion a cripto\"; ademas el portafolio tiene 40.5% en equity_tech (limite 40.0% para perfil moderado)."})
```

Decisiones de re-planificacion:

- R6 preferencia: el cliente pidio 'Recuerda que no quiero aumentar mi exposicion a cripto' -> la recomendacion no puede aumentar exposicion en ETH
- R3 riesgo: ETH excede tolerancia (24.6% > 12%) -> se agrega T7 registrar_alerta (P1, severidad alta)
- R3 riesgo: se agrega T8 evaluar_concentracion (P3) para dimensionar cuanto reducir
- R5 concentracion: equity_tech pesa 40.5% (> 40.0%) -> se agrega T9 registrar_alerta (P2)

Plan final:

```
T1 [completada] P1 consultar_portafolio({"ticker": "ETH"}) - Validar que el cliente tiene posicion en el activo antes de analizar
T2 [completada] P1 recordar_memoria({"consulta": "Que hago con ETH?", "ticker": "ETH"}) - Recuperar recomendaciones previas y preferencias del cliente
T3 [completada] P1 consultar_mercado({"ticker": "ETH"}) - Obtener precio, volatilidad y frescura del dato
T7 [completada] P1 registrar_alerta({"ticker": "ETH", "severidad": "alta", "motivo": "volatilidad 24.6% supera tolerancia 12% del cliente"}) - Riesgo sobre la tolerancia: se notifica al asesor antes de seguir
T4 [completada] P2 evaluar_riesgo({"ticker": "ETH"}) - Cruzar volatilidad del activo con la tolerancia del cliente
T9 [completada] P2 registrar_alerta({"ticker": "PORTAFOLIO", "severidad": "media", "motivo": "exposicion a equity_tech 40.5% supera el limite 40.0% del perfil moderado"}) - Concentracion por sobre el limite del perfil
T5 [completada] P3 buscar_noticias({"ticker": "ETH"}) - Complementar con sentimiento de noticias recientes
T8 [completada] P3 evaluar_concentracion({}) - Medir el impacto del activo riesgoso en la exposicion total
T6 [completada] P4 generar_informe({"ticker": "ETH"}) - Dejar registro escrito y trazable de la recomendacion
```

Respuesta:

> Recomendacion para ETH: reducir posicion.
> Justificacion: la volatilidad a 7 dias (24.6%) supera la tolerancia del cliente (12%) por 12.6 puntos; se respeta la preferencia registrada del cliente: "Recuerda que no quiero aumentar mi exposicion a cripto"; ademas el portafolio tiene 40.5% en equity_tech (limite 40.0% para perfil moderado).
> Alertas registradas para tu asesor: [alta] ETH: volatilidad 24.6% supera tolerancia 12% del cliente; [media] PORTAFOLIO: exposicion a equity_tech 40.5% supera el limite 40.0% del perfil moderado

## Escenario 5 - Activo fuera del portafolio

La validacion inicial (P1) falla y el agente cancela el resto del plan.

**Cliente:** `constanza_fuentes` | **Pregunta:** "Deberia comprar NVDA?"

Herramientas ejecutadas:

```
1. consultar_portafolio({"ticker": "NVDA"})
```

Decisiones de re-planificacion:

- R1 validacion: NVDA no esta en el portafolio -> se cancelan T2, T3, T4, T5, T6 y se responde sin recomendar

Plan final:

```
T1 [completada] P1 consultar_portafolio({"ticker": "NVDA"}) - Validar que el cliente tiene posicion en el activo antes de analizar
T2 [cancelada] P1 recordar_memoria({"consulta": "Deberia comprar NVDA?", "ticker": "NVDA"}) - Recuperar recomendaciones previas y preferencias del cliente | cancelada: activo fuera del portafolio
T3 [cancelada] P1 consultar_mercado({"ticker": "NVDA"}) - Obtener precio, volatilidad y frescura del dato | cancelada: activo fuera del portafolio
T4 [cancelada] P2 evaluar_riesgo({"ticker": "NVDA"}) - Cruzar volatilidad del activo con la tolerancia del cliente | cancelada: activo fuera del portafolio
T5 [cancelada] P3 buscar_noticias({"ticker": "NVDA"}) - Complementar con sentimiento de noticias recientes | cancelada: activo fuera del portafolio
T6 [cancelada] P4 generar_informe({"ticker": "NVDA"}) - Dejar registro escrito y trazable de la recomendacion | cancelada: activo fuera del portafolio
```

Respuesta:

> Recomendacion para NVDA: sin recomendacion.
> Justificacion: Constanza Fuentes no tiene posicion en NVDA. Solo se analizan activos del portafolio del cliente.

## Escenario 6 - Revision de portafolio con priorizacion

El plan recorre las posiciones de mayor a menor peso y antepone las alertas (P1) a medida que detecta activos sobre la tolerancia.

**Cliente:** `constanza_fuentes` | **Pregunta:** "Revisa mi portafolio completo"

Herramientas ejecutadas:

```
1. recordar_memoria({"consulta": "Revisa mi portafolio completo", "ticker": null})
2. evaluar_concentracion({})
3. evaluar_riesgo({"ticker": "BND"})
4. evaluar_riesgo({"ticker": "AAPL"})
5. evaluar_riesgo({"ticker": "TSLA"})
6. registrar_alerta({"ticker": "TSLA", "severidad": "alta", "motivo": "volatilidad 21.8% supera tolerancia 12% del cliente"})
7. evaluar_riesgo({"ticker": "ETH"})
8. registrar_alerta({"ticker": "ETH", "severidad": "alta", "motivo": "volatilidad 24.6% supera tolerancia 12% del cliente"})
9. evaluar_riesgo({"ticker": "VNQ"})
10. registrar_alerta({"ticker": "PORTAFOLIO", "severidad": "media", "motivo": "exposicion a equity_tech 40.5% supera el limite 40.0% del perfil moderado"})
11. generar_informe({"ticker": "PORTAFOLIO", "recomendacion": "reducir ETH, TSLA (en ese orden de prioridad)", "justificacion": "ETH: volatilidad 24.6% vs tolerancia 12%; TSLA: volatilidad 21.8% vs tolerancia 12%; exposicion a equity_tech 40.5% sobre el limite 40.0%."})
```

Decisiones de re-planificacion:

- R5 concentracion: equity_tech pesa 40.5% (> 40.0%) -> se agrega T9 registrar_alerta (P2)
- R3 riesgo: TSLA excede tolerancia (21.8% > 12%) -> se agrega T10 registrar_alerta (P1, severidad alta)
- R3 riesgo: ETH excede tolerancia (24.6% > 12%) -> se agrega T11 registrar_alerta (P1, severidad alta)

Plan final:

```
T1 [completada] P1 recordar_memoria({"consulta": "Revisa mi portafolio completo", "ticker": null}) - Recuperar preferencias y recomendaciones previas del cliente
T2 [completada] P1 evaluar_concentracion({}) - Medir exposicion por clase de activo frente al perfil de riesgo
T10 [completada] P1 registrar_alerta({"ticker": "TSLA", "severidad": "alta", "motivo": "volatilidad 21.8% supera tolerancia 12% del cliente"}) - Riesgo sobre la tolerancia: se notifica al asesor antes de seguir
T11 [completada] P1 registrar_alerta({"ticker": "ETH", "severidad": "alta", "motivo": "volatilidad 24.6% supera tolerancia 12% del cliente"}) - Riesgo sobre la tolerancia: se notifica al asesor antes de seguir
T3 [completada] P2 evaluar_riesgo({"ticker": "BND"}) - Revisar BND (30.0% del portafolio); mayor peso primero
T4 [completada] P2 evaluar_riesgo({"ticker": "AAPL"}) - Revisar AAPL (22.5% del portafolio); mayor peso primero
T5 [completada] P2 evaluar_riesgo({"ticker": "TSLA"}) - Revisar TSLA (18.0% del portafolio); mayor peso primero
T6 [completada] P2 evaluar_riesgo({"ticker": "ETH"}) - Revisar ETH (15.0% del portafolio); mayor peso primero
T7 [completada] P2 evaluar_riesgo({"ticker": "VNQ"}) - Revisar VNQ (14.5% del portafolio); mayor peso primero
T9 [completada] P2 registrar_alerta({"ticker": "PORTAFOLIO", "severidad": "media", "motivo": "exposicion a equity_tech 40.5% supera el limite 40.0% del perfil moderado"}) - Concentracion por sobre el limite del perfil
T8 [completada] P4 generar_informe({"ticker": "PORTAFOLIO"}) - Dejar registro escrito de la revision
```

Respuesta:

> Recomendacion para tu portafolio: reducir ETH, TSLA (en ese orden de prioridad).
> Justificacion: ETH: volatilidad 24.6% vs tolerancia 12%; TSLA: volatilidad 21.8% vs tolerancia 12%; exposicion a equity_tech 40.5% sobre el limite 40.0%.
> Alertas registradas para tu asesor: [alta] TSLA: volatilidad 21.8% supera tolerancia 12% del cliente; [alta] ETH: volatilidad 24.6% supera tolerancia 12% del cliente; [media] PORTAFOLIO: exposicion a equity_tech 40.5% supera el limite 40.0% del perfil moderado
