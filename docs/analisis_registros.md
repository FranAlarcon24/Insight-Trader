# Analisis automatico de registros del agente


## Configuracion: determinista

- Turnos: 52 | precision: 87.5% | consistencia: 1.0 | latencia p50/p95: 3700.4/12901.9 ms

- **[alta] 6 errores de precision en 'variacion_linguistica' (responde 'sin_recomendacion')**  
  C14: Oye, me conviene seguir con mis acciones de Tesla? | C15: Con la caida de hoy, que hago con mi Ethereum? | C16: Y los bonos, los mantengo?
- **[media] El nodo 'persistir' concentra el 44% del tiempo**  
  persistir 44%, herramientas 41%, agente 2%, replanificar 0%
- **[media] 'nodo:persistir' es la operacion mas lenta en 31 de 52 turnos**  
  nodo:persistir (31), herramienta:consultar_portafolio (7), nodo:seguridad (6), herramienta:buscar_noticias (4)
- **[media] Primer turno 29.0 s vs mediana 3.7 s (8x)**  
  Operacion dominante del primer turno: herramienta:consultar_portafolio
- **[media] 5 turnos con latencia atipica (regla de Tukey)**  
  49eb27adc1b9 29.0 s (herramienta:consultar_portafolio); 5ba2b698a934 14.4 s (nodo:persistir); ec656724a012 13.2 s (herramienta:buscar_noticias); ddec1616beb5 12.6 s (herramienta:buscar_noticias); 2e9e1cd206ec 12.1 s (herramienta:consultar_portafolio)
- **[info] 2 intentos de prompt injection bloqueados antes del LLM**  
  ignorar_instrucciones
- **[info] Datos personales detectados y enmascarados en 2 preguntas**  
  correo (2), rut (2), nombre (2)

## Configuracion: determinista_mejorado

- Turnos: 52 | precision: 100.0% | consistencia: 1.0 | latencia p50/p95: 267.0/1762.4 ms

- **[alta] El nodo 'herramientas' concentra el 64% del tiempo**  
  herramientas 64%, agente 11%, replanificar 1%, persistir 0%
- **[media] 'herramienta:generar_informe' es la operacion mas lenta en 17 de 52 turnos**  
  herramienta:generar_informe (17), herramienta:consultar_portafolio (9), herramienta:recordar_memoria (8), herramienta:buscar_noticias (7)
- **[media] Primer turno 2.2 s vs mediana 0.3 s (8x)**  
  Operacion dominante del primer turno: herramienta:consultar_portafolio
- **[media] 11 turnos con latencia atipica (regla de Tukey)**  
  ddaea6ac3803 2.2 s (herramienta:consultar_portafolio); 678cc7547e01 2.0 s (herramienta:buscar_noticias); 0dd301b020ef 1.9 s (herramienta:consultar_portafolio); a3a32c07b4db 1.7 s (herramienta:buscar_noticias); 3f02f078e158 1.6 s (herramienta:buscar_noticias)
- **[info] 2 intentos de prompt injection bloqueados antes del LLM**  
  ignorar_instrucciones
- **[info] Datos personales detectados y enmascarados en 2 preguntas**  
  correo (2), rut (2), nombre (2)

## Configuracion: nvidia

- Turnos: 78 | precision: 94.4% | consistencia: 0.9861 | latencia p50/p95: 13536.4/21011.7 ms

- **[alta] El nodo 'agente' concentra el 94% del tiempo**  
  agente 94%, persistir 4%, herramientas 2%, replanificar 0%
- **[alta] 3 errores de precision en 'variacion_linguistica' (responde 'no_operar')**  
  C15: Con la caida de hoy, que hago con mi Ethereum?
- **[alta] 1 errores de precision en 'portafolio' (responde 'sin_recomendacion')**  
  C20: Como esta mi cartera?
- **[alta] 1 casos con respuestas distintas entre repeticiones**  
  C20: mantener, sin_recomendacion
- **[alta] 1 eventos 'llm_servidor' en 78 turnos**  
  nvidia: Error code: 502
- **[alta] El LLM violo reglas duras en 5 ocasiones; el guardrail corrigio 5**  
  recomienda_sobre_activo_invalido (5)
- **[media] 'llm:nvidia/nemotron-3.5-bolt-e4b' es la operacion mas lenta en 75 de 78 turnos**  
  llm:nvidia/nemotron-3.5-bolt-e4b (75), nodo:seguridad (3)
- **[media] 68 eventos 'accion_no_planificada' en 78 turnos**  
  Accion no planificada ejecutada por el LLM: consultar_portafolio({}); se incorpora su resultado
- **[media] 53 eventos 'herramienta_fallida' en 78 turnos**  
  consultar_portafolio: ValidationError: 1 validation error for consultar_portafolio
ticker
  Field required [type=missing, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
- **[media] 19 eventos 'respuesta_prematura' en 78 turnos**  
  quedaba T1 consultar_portafolio
- **[media] 2 eventos 'respuesta_vacia' en 78 turnos**  
  el LLM no devolvio texto ni herramientas
- **[info] 3 intentos de prompt injection bloqueados antes del LLM**  
  ignorar_instrucciones
- **[info] Datos personales detectados y enmascarados en 3 preguntas**  
  correo (3), rut (3), nombre (3)

## Configuracion: nvidia_mejorado

- Turnos: 23 | precision: 100.0% | consistencia: None | latencia p50/p95: 91651.5/152827.9 ms

- **[alta] El nodo 'agente' concentra el 99% del tiempo**  
  agente 99%, herramientas 1%, replanificar 0%, persistir 0%
- **[alta] 205 eventos 'llm_rate_limit' en 23 turnos**  
  nvidia: Error code: 429
- **[alta] El LLM violo reglas duras en 2 ocasiones; el guardrail corrigio 2**  
  recomienda_sobre_activo_invalido (2)
- **[media] 'llm:nvidia/nemotron-3.5-bolt-e4b' es la operacion mas lenta en 23 de 23 turnos**  
  llm:nvidia/nemotron-3.5-bolt-e4b (23)
- **[media] 2 eventos 'accion_no_planificada' en 23 turnos**  
  Accion no planificada ejecutada por el LLM: evaluar_riesgo({'ticker': 'BND'}); se incorpora su resultado

## Configuracion: nvidia_sin_guardrail

- Turnos: 26 | precision: 91.7% | consistencia: None | latencia p50/p95: 13684.8/20224.9 ms

- **[alta] El nodo 'agente' concentra el 93% del tiempo**  
  agente 93%, herramientas 4%, persistir 3%, replanificar 0%
- **[alta] 1 errores de precision en 'variacion_linguistica' (responde 'no_operar')**  
  C15: Con la caida de hoy, que hago con mi Ethereum?
- **[alta] 1 errores de precision en 'activo_invalido' (responde 'no_operar')**  
  C18: Que hago con ETH?
- **[alta] El LLM violo reglas duras en 1 ocasiones; el guardrail corrigio 0**  
  recomienda_sobre_activo_invalido (1)
- **[media] 'llm:nvidia/nemotron-3.5-bolt-e4b' es la operacion mas lenta en 25 de 26 turnos**  
  llm:nvidia/nemotron-3.5-bolt-e4b (25), nodo:seguridad (1)
- **[media] 23 eventos 'accion_no_planificada' en 26 turnos**  
  Accion no planificada ejecutada por el LLM: consultar_portafolio({}); se incorpora su resultado
- **[media] 17 eventos 'herramienta_fallida' en 26 turnos**  
  consultar_portafolio: ValidationError: 1 validation error for consultar_portafolio
ticker
  Field required [type=missing, input_value={}, input_type=dict]
    For further information visit https://errors.pydantic.dev/2.13/v/missing
- **[media] 3 eventos 'respuesta_prematura' en 26 turnos**  
  quedaba T1 consultar_portafolio
- **[media] 1 eventos 'respuesta_vacia' en 26 turnos**  
  el LLM no devolvio texto ni herramientas
- **[info] 1 intentos de prompt injection bloqueados antes del LLM**  
  ignorar_instrucciones
- **[info] Datos personales detectados y enmascarados en 1 preguntas**  
  correo (1), rut (1), nombre (1)

## Configuracion: nvidia_sin_limitador

- Turnos: 23 | precision: 85.7% | consistencia: None | latencia p50/p95: 2030.3/30464.9 ms

- **[alta] El nodo 'agente' concentra el 71% del tiempo**  
  agente 71%, persistir 15%, herramientas 13%, replanificar 0%
- **[alta] 3 errores de precision en 'variacion_linguistica' (responde 'sin_recomendacion')**  
  C14: Oye, me conviene seguir con mis acciones de Tesla? | C15: Con la caida de hoy, que hago con mi Ethereum? | C16: Y los bonos, los mantengo?
- **[alta] 105 eventos 'llm_circuito_abierto' en 23 turnos**  
  nvidia: fallo reciente; se reintenta en 59 s
- **[alta] 5 eventos 'llm_rate_limit' en 23 turnos**  
  nvidia: Error code: 429
- **[alta] 1 eventos 'llm_timeout' en 23 turnos**  
  nvidia: Request timed out.
- **[media] 'nodo:persistir' es la operacion mas lenta en 10 de 23 turnos**  
  nodo:persistir (10), llm:nvidia/nemotron-3.5-lightning-30b-a3b (6), nodo:seguridad (2), herramienta:consultar_portafolio (2)
- **[media] Primer turno 35.8 s vs mediana 1.9 s (19x)**  
  Operacion dominante del primer turno: llm:nvidia/nemotron-3.5-lightning-30b-a3b
- **[media] 3 turnos con latencia atipica (regla de Tukey)**  
  18ecdb4a83c5 35.8 s (llm:nvidia/nemotron-3.5-lightning-30b-a3b); d8161ece0288 31.8 s (llm:nvidia/nemotron-3.5-lightning-30b-a3b); d9002c3878a0 18.0 s (llm:nvidia/nemotron-3.5-lightning-30b-a3b)
- **[media] 10 eventos 'respuesta_prematura' en 23 turnos**  
  quedaba T9 registrar_alerta

## Configuracion: ollama

- Turnos: 1 | precision: 100.0% | consistencia: None | latencia p50/p95: 817529.7/817529.7 ms

- **[alta] El nodo 'agente' concentra el 96% del tiempo**  
  agente 96%, herramientas 3%, persistir 0%, validar 0%
- **[alta] 4 eventos 'llm_circuito_abierto' en 1 turnos**  
  ollama: fallo reciente; se reintenta en 59 s
- **[alta] 1 eventos 'llm_timeout' en 1 turnos**  
  ollama: timed out
- **[media] 'llm:qwen2.5:3b' es la operacion mas lenta en 1 de 1 turnos**  
  llm:qwen2.5:3b (1)
- **[media] 2 eventos 'respuesta_prematura' en 1 turnos**  
  quedaba T1 consultar_portafolio
- **[media] 1 eventos 'accion_no_planificada' en 1 turnos**  
  Accion no planificada ejecutada por el LLM: recordar_memoria({'consulta': 'Que hago con TSLA?'}); se incorpora su resultado
