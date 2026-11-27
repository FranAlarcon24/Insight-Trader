"""Guardrails del agente (EP3, IE8): controles antes y despues del LLM.

Entrada (`check_input`): bloquea intentos de prompt injection y registra si
la pregunta trae datos personales (que se enmascaran antes de salir hacia
el proveedor de LLM).

Salida (`validate_output`): compara la accion que redacto el LLM con la que
exigen las reglas duras del dominio, calculadas a partir de los hallazgos
de las herramientas (no del texto del LLM):

- datos no confiables          -> solo "no operar"
- activo fuera del portafolio  -> solo "sin recomendacion"
- volatilidad > tolerancia     -> no se puede "mantener"
- preferencia restrictiva      -> no se puede sugerir aumentar exposicion
- respuesta sin recomendacion reconocible -> formato invalido

Si hay violacion y el guardrail esta activo, la respuesta se reemplaza por
la del planificador determinista y queda registrado el motivo. Con el
guardrail apagado solo se registra (sirve para medir cuanto se equivoca el
LLM por si solo).
"""
from __future__ import annotations

import re

from insight_trader.agent.llm import _plain, classify_action, decide
from insight_trader.agent.planner import PORTFOLIO_MODE
from insight_trader.observability.privacy import detect_injection, pii_found

DISCLAIMER = ("Nota: recomendacion de apoyo para tu asesor; no es una orden de inversion. "
              "La decision final la toma una persona.")

_VERBS = r"(?:aumentar|incrementar|comprar mas|sumar mas|acumular)"
_INCREASE = re.compile(rf"\b{_VERBS}\b")
# "sin aumentar", "no debes aumentar"... no contradicen la preferencia
_NEGATED = re.compile(rf"\b(?:sin|no|evitar|evita|nunca)\s+(?:\w+\s+){{0,2}}{_VERBS}\b")


def check_input(question: str) -> dict:
    injection = detect_injection(question)
    return {
        "bloqueado": bool(injection),
        "inyeccion": injection,
        "pii_entrada": pii_found(question),
    }


def blocked_answer(patterns: list[str]) -> str:
    return ("Solicitud bloqueada por seguridad: la pregunta intenta modificar las reglas del agente "
            f"({', '.join(patterns)}). Reformula tu consulta sobre un activo de tu portafolio.")


def expected_category(findings: dict) -> str:
    action, _ = decide(findings)
    return classify_action(f"Recomendacion para X: {action}.")


def validate_output(answer: str, findings: dict) -> list[str]:
    """Lista de reglas duras que la respuesta viola (vacia = valida)."""
    if findings["ticker"] is None:
        return []
    got = classify_action(answer)
    violations = []
    if findings["error"]:
        if got != "sin_recomendacion":
            violations.append("recomienda_sobre_activo_invalido")
        return violations
    if not findings["datos_confiables"] and got != "no_operar":
        violations.append("opera_con_datos_desactualizados")
    if findings["ticker"] != PORTFOLIO_MODE:
        risk = findings["riesgo"].get(findings["ticker"])
        if risk and risk.get("excede_tolerancia") and findings["datos_confiables"] and got == "mantener":
            violations.append("ignora_tolerancia_al_riesgo")
    if findings["restricciones"] and _INCREASE.search(_NEGATED.sub("", _plain(answer))):
        violations.append("contradice_preferencia_del_cliente")
    if got == "otro":
        violations.append("formato_sin_recomendacion")
    return violations
