"""Herramientas del agente (IE1), agrupadas por tipo de capacidad:

- Consulta:      consultar_portafolio, consultar_mercado, buscar_noticias,
                 recordar_memoria
- Razonamiento:  evaluar_riesgo, evaluar_concentracion
- Escritura:     registrar_alerta, generar_informe, guardar_preferencia

Cada herramienta es un `StructuredTool` de LangChain (decorador `@tool`):
su docstring y type hints generan el esquema JSON que el LLM ve para
decidir cuando y con que argumentos llamarla. Todas devuelven JSON para
que el planificador pueda leer el resultado y re-planificar.

Las herramientas se construyen con `build_tools(ctx)` para inyectar el
cliente, el entorno de mercado y la memoria sin variables globales.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from insight_trader import config
from insight_trader.agent.environment import MAX_DATA_AGE_HOURS, MarketEnvironment, load_environment
from insight_trader.agent.memory import LongTermMemory
from insight_trader.agent.planner import CONCENTRATION_LIMITS, PORTFOLIO_MODE, RISKY_CLASSES
from insight_trader.agents.analysis_agent import AnalysisAgent
from insight_trader.rag.retriever import RAGRetriever

TOOL_GROUPS = {
    "consulta": ("consultar_portafolio", "consultar_mercado", "buscar_noticias", "recordar_memoria"),
    "razonamiento": ("evaluar_riesgo", "evaluar_concentracion"),
    "escritura": ("registrar_alerta", "generar_informe", "guardar_preferencia"),
}


@dataclass
class AgentContext:
    """Dependencias compartidas por las herramientas durante una sesion."""

    client_id: str
    memory: LongTermMemory
    output_dir: Path
    scenario: str = "normal"
    client: dict = field(init=False)
    env: MarketEnvironment = field(init=False)
    retriever: RAGRetriever = field(init=False)
    analysis: AnalysisAgent = field(init=False)

    def __post_init__(self):
        self.client = json.loads(config.client_data_path(self.client_id).read_text(encoding="utf-8"))
        self.set_scenario(self.scenario)

    def set_scenario(self, scenario: str) -> None:
        """Cambia el entorno de mercado en caliente (condicion cambiante)."""
        self.scenario = scenario
        self.env = load_environment(scenario)
        self.retriever = RAGRetriever(self.client_id, market=self.env.market, news=self.env.news)
        self.analysis = AnalysisAgent(self.client_id, market=self.env.market, news=self.env.news)

    def holding(self, ticker: str) -> dict | None:
        return next((h for h in self.client["holdings"] if h["ticker"] == ticker), None)


def _dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def build_tools(ctx: AgentContext) -> list[BaseTool]:
    # ------------------------------------------------------------ consulta

    @tool
    def consultar_portafolio(ticker: str) -> str:
        """Consulta la posicion del cliente en un activo (cantidad, precio promedio,
        peso en el portafolio), su perfil de riesgo y el historial de transacciones
        recuperado desde el indice RAG interno. Usar primero para validar que el
        cliente tiene el activo."""
        holding = ctx.holding(ticker)
        if holding is None:
            return _dump({
                "en_portafolio": False,
                "error": f"{ctx.client['client_name']} no tiene posicion en {ticker}",
                "activos_del_cliente": [h["ticker"] for h in ctx.client["holdings"]],
            })
        chunks = ctx.retriever.retrieve_internal(f"{ticker} transacciones posicion", ticker=ticker)
        return _dump({
            "en_portafolio": True,
            "posicion": {
                "ticker": ticker,
                "nombre": holding["name"],
                "cantidad": holding["quantity"],
                "precio_promedio": holding["avg_buy_price"],
                "peso_pct": holding["current_weight_pct"],
                "clase_activo": holding["asset_class"],
            },
            "perfil_riesgo": ctx.client["risk_profile"],
            "contexto_rag_interno": [c.text for c in chunks],
        })

    @tool
    def consultar_mercado(ticker: str) -> str:
        """Consulta el feed de mercado (precio, cambio y volatilidad a 7 dias,
        tendencia) de un activo e informa si el dato esta fresco o desactualizado."""
        asset = ctx.env.asset(ticker)
        if asset is None:
            return _dump({"error": f"Sin datos de mercado para {ticker}"})
        return _dump({
            "ticker": ticker,
            "precio": asset["price"],
            "cambio_7d_pct": asset["change_7d_pct"],
            "volatilidad_7d_pct": asset["volatility_7d_pct"],
            "tendencia": asset["trend"],
            "fuente": ctx.env.market["source"],
            "as_of": ctx.env.market["as_of"],
            "antiguedad_h": ctx.env.data_age_hours(),
            "datos_frescos": ctx.env.is_fresh(),
        })

    @tool
    def buscar_noticias(ticker: str, consulta: str = "") -> str:
        """Busca noticias financieras recientes del activo en el indice RAG externo
        y devuelve titulares con su sentimiento (positivo/negativo/neutral)."""
        chunks = ctx.retriever.retrieve_external(f"{ticker} noticias {consulta}", ticker=ticker, top_k=5)
        news = [c.text for c in chunks if c.metadata.get("type") == "news"]
        sentiments = [n["sentiment"] for n in ctx.env.news if n["ticker"] == ticker]
        return _dump({
            "ticker": ticker,
            "noticias": news,
            "sentimiento_predominante": sentiments[0] if sentiments else "neutral",
        })

    @tool
    def recordar_memoria(consulta: str, ticker: str | None = None) -> str:
        """Busca en la memoria de largo plazo del cliente (por similitud semantica)
        interacciones y recomendaciones anteriores, y sus preferencias declaradas."""
        similar = ctx.memory.search(ctx.client_id, consulta, ticker=ticker, top_k=3)
        previous = ctx.memory.latest(ctx.client_id, "interaccion", ticker) if ticker else None
        return _dump({
            "recuerdos_relevantes": [m.as_dict() for m in similar],
            "recomendacion_previa": previous.as_dict() | {"accion": previous.metadata.get("accion")}
            if previous else None,
            "preferencias": [p.content for p in ctx.memory.preferences(ctx.client_id)],
        })

    # ------------------------------------------------------------ razonamiento

    @tool
    def evaluar_riesgo(ticker: str) -> str:
        """Cruza la volatilidad reciente del activo con la tolerancia a drawdown del
        cliente y el sentimiento de noticias. Indica si el activo excede la
        tolerancia al riesgo y el margen respecto a ella."""
        try:
            signal = ctx.analysis.run(ticker)
        except ValueError as exc:
            return _dump({"error": str(exc)})
        return _dump({
            "ticker": ticker,
            "perfil": signal.risk_category,
            "tolerancia_pct": signal.risk_tolerance_drawdown_pct,
            "volatilidad_7d_pct": signal.market_volatility_7d_pct,
            "cambio_7d_pct": signal.market_change_7d_pct,
            "tendencia": signal.market_trend,
            "sentimiento": signal.news_sentiment,
            "excede_tolerancia": signal.exceeds_risk_tolerance,
            "margen_pct": round(signal.risk_tolerance_drawdown_pct - signal.market_volatility_7d_pct, 1),
            "antiguedad_h": ctx.env.data_age_hours(),
            "datos_frescos": ctx.env.is_fresh(),
        })

    @tool
    def evaluar_concentracion() -> str:
        """Calcula la exposicion del portafolio por clase de activo y la compara con
        el limite de exposicion a activos de riesgo (tecnologia, cripto) que
        corresponde al perfil del cliente."""
        profile = ctx.client["risk_profile"]["category"]
        limit = CONCENTRATION_LIMITS[profile]
        by_class: dict[str, float] = {}
        for h in ctx.client["holdings"]:
            by_class[h["asset_class"]] = round(by_class.get(h["asset_class"], 0) + h["current_weight_pct"], 1)
        exceeded = [
            {"clase": cls, "peso_pct": w} for cls, w in by_class.items() if cls in RISKY_CLASSES and w > limit
        ]
        return _dump({
            "perfil": profile,
            "limite_pct": limit,
            "exposicion_por_clase": by_class,
            "clases_excedidas": exceeded,
            "posiciones": [
                {"ticker": h["ticker"], "peso_pct": h["current_weight_pct"], "clase": h["asset_class"]}
                for h in ctx.client["holdings"]
            ],
        })

    # ------------------------------------------------------------ escritura

    @tool
    def registrar_alerta(ticker: str, motivo: str, severidad: str = "media") -> str:
        """Registra una alerta de riesgo para el asesor humano (archivo
        alertas.jsonl). Severidad: media, alta o critica."""
        ctx.output_dir.mkdir(parents=True, exist_ok=True)
        alert = {
            "fecha": datetime.now().isoformat(timespec="seconds"),
            "cliente": ctx.client_id,
            "escenario": ctx.scenario,
            "ticker": ticker,
            "severidad": severidad,
            "motivo": motivo,
        }
        with (ctx.output_dir / "alertas.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(alert, ensure_ascii=False) + "\n")
        return _dump({"registrada": True, **alert})

    @tool
    def generar_informe(ticker: str, recomendacion: str, justificacion: str) -> str:
        """Escribe el informe final de la recomendacion en Markdown (carpeta
        outputs/informes) para que el asesor y el cliente lo revisen."""
        folder = ctx.output_dir / "informes"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = folder / f"{ctx.client_id}_{ticker}_{ctx.scenario}_{stamp}.md"
        title = "Revision de portafolio" if ticker == PORTFOLIO_MODE else f"Recomendacion {ticker}"
        path.write_text(
            f"# {title} - {ctx.client['client_name']}\n\n"
            f"- Escenario de mercado: {ctx.scenario}\n"
            f"- Datos de mercado al: {ctx.env.market['as_of']} "
            f"(limite de frescura {MAX_DATA_AGE_HOURS} h)\n"
            f"- Perfil: {ctx.client['risk_profile']['category']}\n\n"
            f"## Recomendacion\n\n{recomendacion}\n\n## Justificacion\n\n{justificacion}\n",
            encoding="utf-8",
        )
        return _dump({"ruta": str(path)})

    @tool
    def guardar_preferencia(preferencia: str) -> str:
        """Guarda en la memoria de largo plazo una preferencia o restriccion
        declarada por el cliente (ej. 'no quiero aumentar mi exposicion a cripto')."""
        memory_id = ctx.memory.remember(ctx.client_id, "preferencia", preferencia)
        return _dump({"guardada": True, "id": memory_id, "preferencia": preferencia})

    return [
        consultar_portafolio, consultar_mercado, buscar_noticias, recordar_memoria,
        evaluar_riesgo, evaluar_concentracion,
        registrar_alerta, generar_informe, guardar_preferencia,
    ]
