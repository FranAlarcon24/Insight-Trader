"""Configuracion comun de las pruebas.

Las pruebas usan el planificador determinista (sin LLM) y embeddings por
hashing: son rapidas, reproducibles y no dependen de red ni de Ollama. Las
variables se fijan antes de importar `insight_trader.config`.
"""
import os

os.environ["INSIGHT_TRADER_LLM_PROVIDER"] = "mock"
os.environ["INSIGHT_TRADER_EMBEDDINGS"] = "hash"
os.environ.setdefault("INSIGHT_TRADER_GUARDRAIL", "on")
