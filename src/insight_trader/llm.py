"""Interfaz de LLM intercambiable: mock (offline) o Anthropic (real).

El resto del pipeline solo depende de `BaseLLM.generate(prompt: str) -> str`,
por lo que cambiar de mock a un proveedor real no requiere tocar los agentes.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod

from insight_trader import config


class BaseLLM(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class MockLLM(BaseLLM):
    """LLM simulado: sintetiza una recomendacion citando literalmente los
    datos entregados en el prompt, para poder probar el pipeline completo
    sin costo ni API key. La logica de sintesis es deliberadamente simple
    (reglas + extraccion de cifras) ya que su unico rol es imitar el
    contrato de salida de un LLM real para fines de esta evaluacion.
    """

    def generate(self, prompt: str) -> str:
        ticker_match = re.search(r"Activo objetivo:\s*(\w+)", prompt)
        ticker = ticker_match.group(1) if ticker_match else "el activo"

        volatility_match = re.search(r"senal_volatilidad_7d_pct:\s*([\d.\-]+)", prompt)
        change_match = re.search(r"senal_cambio_7d_pct:\s*([\d.\-]+)", prompt)
        risk_match = re.search(r"senal_tolerancia_drawdown_pct:\s*([\d.\-]+)", prompt)
        sentiment_match = re.search(r"senal_sentimiento:\s*(\w+)", prompt)

        volatility = float(volatility_match.group(1)) if volatility_match else None
        change = float(change_match.group(1)) if change_match else None
        risk_tolerance = float(risk_match.group(1)) if risk_match else None
        sentiment = sentiment_match.group(1) if sentiment_match else "neutral"

        if volatility is not None and risk_tolerance is not None and volatility > risk_tolerance:
            action = "reducir posicion"
            razon = (
                f"la volatilidad reciente ({volatility}%) supera la tolerancia al riesgo "
                f"declarada por el cliente ({risk_tolerance}%)"
            )
        elif change is not None and change > 5 and sentiment == "positivo":
            action = "mantener posicion"
            razon = (
                f"el activo muestra una tendencia positiva ({change}% en 7 dias) respaldada "
                f"por noticias de sentimiento {sentiment}, dentro del rango de riesgo tolerado"
            )
        elif change is not None and change < -2:
            action = "mantener posicion y monitorear"
            razon = f"el activo presenta una caida reciente ({change}% en 7 dias) que amerita seguimiento"
        else:
            action = "mantener posicion"
            razon = "no se detectan senales que justifiquen un cambio respecto al perfil de riesgo del cliente"

        return (
            f"Recomendacion para {ticker}: {action}.\n"
            f"Justificacion: Se sugiere {action} porque {razon}. "
            f"Esta recomendacion se basa en datos de mercado y perfil de riesgo recuperados por el sistema, "
            f"citados explicitamente arriba."
        )


class AnthropicLLM(BaseLLM):
    """Wrapper real sobre la API de Anthropic. Requiere ANTHROPIC_API_KEY.

    Se deja implementado para produccion, pero no se ejecuta en las pruebas
    de esta entrega (no se dispone de API key); el proyecto corre por
    defecto con MockLLM (ver `insight_trader.config.LLM_PROVIDER`).
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or config.ANTHROPIC_API_KEY
        self.model = model or config.ANTHROPIC_MODEL
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY no esta configurada. Define la variable de entorno "
                "o usa INSIGHT_TRADER_LLM_PROVIDER=mock para pruebas sin costo."
            )

    def generate(self, prompt: str) -> str:
        import anthropic  # import diferido: solo se necesita si se usa este proveedor

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text


def get_llm(provider: str | None = None) -> BaseLLM:
    provider = provider or config.LLM_PROVIDER
    if provider == "anthropic":
        return AnthropicLLM()
    return MockLLM()
