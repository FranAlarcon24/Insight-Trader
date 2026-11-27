"""Privacidad y seguridad de entrada (EP3, IE8).

Tres protecciones que se aplican antes de que un texto salga del proceso
(hacia la API de NVIDIA, un tercero) o quede escrito en logs y trazas:

1. `mask_pii`: enmascara RUT, correo, telefono, tarjeta y los nombres de
   los clientes conocidos. Principio de minimizacion de datos (Ley 19.628
   y Ley 21.719 de proteccion de datos personales en Chile).
2. `pseudonym`: reemplaza el id del cliente por un seudonimo estable
   (hash con sal). Las trazas siguen siendo agregables por cliente sin
   exponer su identidad.
3. `detect_injection`: patrones de prompt injection / jailbreak en la
   pregunta del usuario (OWASP Top 10 para LLM, LLM01).
"""
from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache

from insight_trader import config

# RUT chileno: 12.345.678-9 / 12345678-9 / 12.345.678-K
_RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
# Tarjeta: 13 a 19 digitos, con o sin espacios/guiones cada 4
_CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
# Telefono chileno: +56 9 1234 5678 / 912345678 / +56 2 2345 6789
_PHONE = re.compile(r"(?:\+?56[ -]?)?\b9[ -]?\d{4}[ -]?\d{4}\b|\+56[ -]?2[ -]?\d{4}[ -]?\d{4}\b")

_INJECTION_PATTERNS = [
    (r"ignora\w*\s+(?:todas?\s+)?(?:las\s+|tus\s+)?(?:instrucciones|reglas|indicaciones)", "ignorar_instrucciones"),
    (r"olvida\w*\s+(?:todo|las\s+reglas|tus\s+instrucciones)", "olvidar_reglas"),
    (r"ignore\s+(?:all\s+|the\s+)?(?:previous|above)?\s*instructions", "ignore_instructions"),
    (r"(?:muestra|revela|imprime|dime)\w*\s+(?:tu|el)\s+(?:prompt|system\s*prompt|instrucciones\s+de\s+sistema)",
     "exfiltrar_prompt"),
    (r"system\s*prompt", "exfiltrar_prompt"),
    (r"(?:act[uú]a|comp[oó]rtate|haz\s+de\s+cuenta)\s+como\s+(?:si\s+)?(?:fueras|un|una)", "cambio_de_rol"),
    (r"modo\s+(?:desarrollador|dios|sin\s+restricciones)|jailbreak|\bDAN\b", "jailbreak"),
    (r"(?:datos|portafolio|posiciones)\s+de\s+otr[oa]s?\s+client", "acceso_otros_clientes"),
    (r"(?:sin|omite|salta\w*)\s+(?:las\s+)?(?:alertas|validaciones|reglas)", "evadir_controles"),
]
_INJECTION = [(re.compile(p, re.I), label) for p, label in _INJECTION_PATTERNS]


@lru_cache(maxsize=1)
def _known_names() -> tuple[str, ...]:
    """Nombres de los clientes conocidos (y sus partes), del mas largo al
    mas corto para que 'Constanza Fuentes' se reemplace antes que 'Fuentes'."""
    names: set[str] = set()
    for client_id in config.list_client_ids():
        try:
            data = json.loads(config.client_data_path(client_id).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        names.add(client_id)  # el id (ej. diego_herrera) tambien identifica
        full = data.get("client_name", "")
        if full:
            names.add(full)
            names.update(part for part in full.split() if len(part) > 3)
    return tuple(sorted(names, key=len, reverse=True))


def mask_pii(text: str | None) -> str | None:
    if not text:
        return text
    text = _EMAIL.sub("[CORREO]", text)
    text = _RUT.sub("[RUT]", text)
    text = _CARD.sub("[TARJETA]", text)
    text = _PHONE.sub("[TELEFONO]", text)
    for name in _known_names():
        replacement = pseudonym(name) if "_" in name else "[NOMBRE]"
        # \b no separa "diego_herrera_AAPL" (el _ es caracter de palabra)
        text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])", replacement, text, flags=re.I)
    return text


def pii_found(text: str) -> list[str]:
    """Tipos de dato personal presentes en el texto (para auditoria)."""
    kinds = []
    for label, pattern in (("correo", _EMAIL), ("rut", _RUT), ("tarjeta", _CARD), ("telefono", _PHONE)):
        if pattern.search(text):
            kinds.append(label)
    if any(re.search(rf"\b{re.escape(n)}\b", text, re.I) for n in _known_names()):
        kinds.append("nombre")
    return kinds


def pseudonym(client_id: str) -> str:
    digest = hashlib.sha256(f"{config.PSEUDONYM_SALT}:{client_id}".encode()).hexdigest()
    return f"cli_{digest[:8]}"


def detect_injection(text: str) -> list[str]:
    return sorted({label for pattern, label in _INJECTION if pattern.search(text)})
