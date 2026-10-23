"""Orquestacion del agente con LangGraph (IE1, IE2, IE3).

Grafo de estados:

    START -> interpretar -> planificar -> agente <-> herramientas -> replanificar
                                            |                          |
                                            |  (sin tool calls)        +--> agente
                                            v
                                        persistir -> END

- interpretar:  identifica el activo de la pregunta; si no se menciona, lo
                hereda del turno anterior (memoria de corto plazo).
- planificar:   arma el plan priorizado (planner.initial_plan).
- agente:       el LLM recibe plan + hallazgos + historial reciente y decide
                la siguiente herramienta o la respuesta final.
- herramientas: ToolNode de LangGraph ejecuta las tool calls.
- replanificar: observa los resultados y ajusta el plan (planner.replan).
- persistir:    guarda la interaccion en la memoria de largo plazo.

El estado completo se guarda por `thread_id` con un checkpointer
(`InMemorySaver`), lo que da continuidad entre turnos de una conversacion.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from insight_trader import config
from insight_trader.agent import planner
from insight_trader.agent.llm import SYSTEM_PROMPT, compose_answer, get_chat_model
from insight_trader.agent.memory import LongTermMemory
from insight_trader.agent.tools import AgentContext, build_tools


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    ticker: str | None  # activo en foco; persiste entre turnos (corto plazo)
    question: str
    turn_start: int  # indice del mensaje que inicia el turno actual
    tasks: list[dict]
    initial_tasks: list[dict]
    findings: dict
    plan_log: list[str]
    trace: list[dict]  # un registro por herramienta ejecutada (para la vista web)
    steps: int


@dataclass
class AgentResult:
    respuesta: str
    accion: str | None
    ticker: str | None
    plan_inicial: list[dict]
    plan_final: list[dict]
    plan_log: list[str]
    herramientas: list[str]
    pasos: list[dict]
    findings: dict


_ACTION_RE = re.compile(r"Recomendacion para [^:]+: (.*?)\.\n")


def _previous_turns(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Memoria de corto plazo compacta: de los turnos anteriores solo se
    conservan preguntas y respuestas finales (no las llamadas a
    herramientas), limitadas a una ventana de mensajes recientes."""
    kept = [m for m in messages if isinstance(m, HumanMessage) or (isinstance(m, AIMessage) and not m.tool_calls)]
    kept = kept[-config.SHORT_TERM_WINDOW:]
    while kept and not isinstance(kept[0], HumanMessage):
        kept.pop(0)
    return kept


def build_graph(ctx: AgentContext, model: BaseChatModel, tools: list):
    model_with_tools = model.bind_tools(tools)
    known_tickers = {h["ticker"] for h in ctx.client["holdings"]} | {a["ticker"] for a in ctx.env.market["assets"]}

    def interpretar(state: AgentState) -> dict:
        messages = state["messages"]
        question = messages[-1].content
        log: list[str] = []
        if planner.is_portfolio_request(question):
            ticker = planner.PORTFOLIO_MODE
        else:
            ticker = planner.extract_ticker(question, known_tickers)
            # Una preferencia sin activo ("no quiero mas cripto") no es una
            # pregunta de seguimiento: no se hereda el activo anterior.
            if ticker is None and state.get("ticker") and not planner.states_preference(question):
                ticker = state["ticker"]
                log.append(f"R0 contexto: la pregunta no menciona un activo -> se usa {ticker} del turno "
                           "anterior (memoria de corto plazo)")
        mode = "portafolio" if ticker == planner.PORTFOLIO_MODE else "activo"
        return {
            "question": question,
            "ticker": ticker,
            "turn_start": len(messages) - 1,
            "findings": planner.new_findings(mode, ticker),
            "plan_log": log,
            "trace": [],
            "steps": 0,
        }

    def planificar(state: AgentState) -> dict:
        ticker = state["ticker"]
        if ticker is None:
            # Sin activo: solo se puede guardar una preferencia (si la hay)
            tasks = planner.initial_plan(state["question"], None, ctx.client["holdings"])
            tasks = [t for t in tasks if t["herramienta"] == "guardar_preferencia"]
        else:
            tasks = planner.initial_plan(state["question"], ticker, ctx.client["holdings"])
        return {"tasks": tasks, "initial_tasks": copy.deepcopy(tasks)}

    def agente(state: AgentState) -> dict:
        findings = state["findings"]
        if state["steps"] >= config.MAX_AGENT_STEPS:
            note = f"Limite de {config.MAX_AGENT_STEPS} pasos alcanzado: se cierra con los hallazgos disponibles"
            return {"messages": [AIMessage(content=compose_answer(findings))],
                    "plan_log": state["plan_log"] + [note]}
        risk = ctx.client["risk_profile"]
        system = SystemMessage(content=SYSTEM_PROMPT.format(
            client_name=ctx.client["client_name"],
            risk_category=risk["category"],
            risk_tolerance=risk["max_drawdown_tolerance_pct"],
            scenario=ctx.scenario,
            plan=planner.render_plan(state["tasks"]) or "(sin tareas)",
            findings=json.dumps(findings, ensure_ascii=False),
        ))
        start = state["turn_start"]
        history = _previous_turns(state["messages"][:start]) + state["messages"][start:]
        response = model_with_tools.invoke([system] + history)
        return {"messages": [response], "steps": state["steps"] + 1}

    def replanificar(state: AgentState) -> dict:
        tasks = copy.deepcopy(state["tasks"])
        findings = copy.deepcopy(state["findings"])
        log = list(state["plan_log"])
        trace = list(state["trace"])

        messages = state["messages"]
        tool_messages = []
        i = len(messages) - 1
        while i >= 0 and isinstance(messages[i], ToolMessage):
            tool_messages.insert(0, messages[i])
            i -= 1
        calls = {tc["id"]: tc for tc in messages[i].tool_calls}

        for tm in tool_messages:
            call = calls[tm.tool_call_id]
            try:
                result = json.loads(tm.content)
            except (json.JSONDecodeError, TypeError):
                result = {"error": str(tm.content)}
            decisions = planner.replan(tasks, findings, call["name"], call["args"], result)
            log += decisions
            trace.append({
                "herramienta": call["name"],
                "args": call["args"],
                "resultado": result,
                "decisiones": decisions,
                "plan": copy.deepcopy(tasks),
            })
        return {"tasks": tasks, "findings": findings, "plan_log": log, "trace": trace}

    def persistir(state: AgentState) -> dict:
        findings = state["findings"]
        ticker = state["ticker"]
        if ticker and not findings["error"]:
            answer = state["messages"][-1].content
            match = _ACTION_RE.search(answer + "\n")
            ctx.memory.remember(
                ctx.client_id, "interaccion",
                f"Pregunta: {state['question']} | Respuesta: {answer}",
                ticker=ticker,
                metadata={"accion": match.group(1) if match else None, "escenario": ctx.scenario},
            )
        return {}

    def route_after_agent(state: AgentState) -> str:
        last = state["messages"][-1]
        return "herramientas" if isinstance(last, AIMessage) and last.tool_calls else "persistir"

    graph = StateGraph(AgentState)
    graph.add_node("interpretar", interpretar)
    graph.add_node("planificar", planificar)
    graph.add_node("agente", agente)
    graph.add_node("herramientas", ToolNode(tools))
    graph.add_node("replanificar", replanificar)
    graph.add_node("persistir", persistir)

    graph.add_edge(START, "interpretar")
    graph.add_edge("interpretar", "planificar")
    graph.add_edge("planificar", "agente")
    graph.add_conditional_edges("agente", route_after_agent, ["herramientas", "persistir"])
    graph.add_edge("herramientas", "replanificar")
    graph.add_edge("replanificar", "agente")
    graph.add_edge("persistir", END)
    return graph


class InsightTraderAgent:
    """Fachada del agente: una instancia = un cliente; cada `thread_id` es
    una conversacion independiente con su propia memoria de corto plazo."""

    def __init__(
        self,
        client_id: str = config.DEFAULT_CLIENT_ID,
        scenario: str = "normal",
        memory: LongTermMemory | None = None,
        output_dir: str | Path | None = None,
        model: BaseChatModel | None = None,
    ):
        self.ctx = AgentContext(
            client_id=client_id,
            memory=memory or LongTermMemory(),
            output_dir=Path(output_dir or config.OUTPUT_DIR),
            scenario=scenario,
        )
        self.tools = build_tools(self.ctx)
        self.graph = build_graph(self.ctx, model or get_chat_model(), self.tools).compile(
            checkpointer=InMemorySaver()
        )

    def set_scenario(self, scenario: str) -> None:
        self.ctx.set_scenario(scenario)

    def ask(self, question: str, thread_id: str = "conversacion-1") -> AgentResult:
        state = self.graph.invoke(
            {"messages": [HumanMessage(content=question)]},
            config={"configurable": {"thread_id": thread_id}, "recursion_limit": 4 * config.MAX_AGENT_STEPS},
        )
        turn = state["messages"][state["turn_start"]:]
        executed = [
            f"{tc['name']}({json.dumps(tc['args'], ensure_ascii=False)})"
            for m in turn if isinstance(m, AIMessage) for tc in m.tool_calls
        ]
        answer = state["messages"][-1].content
        action = _ACTION_RE.search(answer + "\n")
        return AgentResult(
            respuesta=answer,
            accion=action.group(1) if action else None,
            ticker=state["ticker"],
            plan_inicial=state["initial_tasks"],
            plan_final=state["tasks"],
            plan_log=state["plan_log"],
            herramientas=executed,
            pasos=state["trace"],
            findings=state["findings"],
        )
