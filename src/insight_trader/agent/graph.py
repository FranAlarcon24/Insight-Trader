"""Orquestacion del agente con LangGraph (EP2 IE1-IE3, EP3 IE1-IE3/IE8).

Grafo de estados:

    START -> seguridad -> interpretar -> planificar -> agente <-> herramientas -> replanificar
                 |                                        |                          |
                 | (prompt injection)                     | (sin tool calls)         +--> agente
                 v                                        v
              bloquear -> END                          validar -> persistir -> END

- seguridad:    guardrail de entrada (prompt injection, datos personales).
- interpretar:  identifica el activo; si no se menciona, lo hereda del turno
                anterior (memoria de corto plazo).
- planificar:   arma el plan priorizado (planner.initial_plan).
- agente:       el LLM (via LLMRouter: NVIDIA -> Ollama -> modo degradado)
                recibe plan + hallazgos + historial y decide la siguiente
                herramienta o la respuesta final.
- herramientas: ToolNode de LangGraph ejecuta las tool calls.
- replanificar: observa los resultados y ajusta el plan (planner.replan).
- validar:      guardrail de salida: la respuesta no puede violar reglas duras.
- persistir:    guarda la interaccion en la memoria de largo plazo.

El estado se guarda por conversacion con un checkpointer SQLite (memoria de
corto plazo que sobrevive a reinicios). Cada turno deja una traza completa
(spans, latencias, tokens, recursos, decisiones) en outputs/observabilidad.
"""
from __future__ import annotations

import copy
import json
import logging
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from insight_trader import config
from insight_trader import config as settings
from insight_trader.agent import guardrails, planner
from insight_trader.agent.llm import SYSTEM_PROMPT, LLMRouter, ProviderError, classify_action, compose_answer
from insight_trader.agent.memory import LongTermMemory
from insight_trader.agent.tools import AgentContext, build_tools
from insight_trader.observability.privacy import mask_pii, pseudonym
from insight_trader.observability.store import TraceStore, setup_logging
from insight_trader.observability.tracing import ResourceMonitor, TraceCollector

log = logging.getLogger("insight_trader.agent")


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
    llm_calls: list[dict]  # una entrada por llamada al LLM (router)
    events: list[dict]  # anomalias del turno (respuesta prematura, limite de pasos...)
    security: dict  # resultado del guardrail de entrada
    guardrail: dict  # resultado del guardrail de salida


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
    accion_categoria: str = "otro"
    proveedor: str | None = None
    degradado: bool = False
    guardrail: dict = field(default_factory=dict)
    seguridad: dict = field(default_factory=dict)
    traza_id: str | None = None
    latencia_ms: float = 0.0


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


def _masked(messages: list[AnyMessage]) -> list[AnyMessage]:
    """Copia de los mensajes sin datos personales: es lo que sale hacia el
    proveedor de LLM (un tercero, en el caso de NVIDIA)."""
    out = []
    for m in messages:
        if isinstance(m.content, str):
            m = m.model_copy(update={"content": mask_pii(m.content)})
        out.append(m)
    return out


def build_graph(ctx: AgentContext, router: LLMRouter, tools: list):
    known_tickers = {h["ticker"] for h in ctx.client["holdings"]} | {a["ticker"] for a in ctx.env.market["assets"]}

    def seguridad(state: AgentState) -> dict:
        question = state["messages"][-1].content
        check = guardrails.check_input(question)
        if check["bloqueado"]:
            log.warning("entrada_bloqueada", extra={"evento": "prompt_injection", "patrones": check["inyeccion"],
                                                    "cliente": pseudonym(ctx.client_id)})
        if check["pii_entrada"]:
            log.info("pii_en_entrada", extra={"evento": "pii_enmascarada", "tipos": check["pii_entrada"],
                                              "cliente": pseudonym(ctx.client_id)})
        return {"security": check, "question": question, "turn_start": len(state["messages"]) - 1,
                "llm_calls": [], "events": [], "guardrail": {}, "trace": [], "plan_log": [], "steps": 0,
                "tasks": [], "initial_tasks": [], "findings": planner.new_findings("activo", None)}

    def bloquear(state: AgentState) -> dict:
        return {"messages": [AIMessage(content=guardrails.blocked_answer(state["security"]["inyeccion"]))]}

    def interpretar(state: AgentState) -> dict:
        question = state["question"]
        log_: list[str] = []
        if planner.is_portfolio_request(question):
            ticker = planner.PORTFOLIO_MODE
        else:
            ticker = planner.extract_ticker(question, known_tickers)
            # Una preferencia sin activo ("no quiero mas cripto") no es una
            # pregunta de seguimiento: no se hereda el activo anterior.
            if ticker is None and state.get("ticker") and not planner.states_preference(question):
                ticker = state["ticker"]
                log_.append(f"R0 contexto: la pregunta no menciona un activo -> se usa {ticker} del turno "
                            "anterior (memoria de corto plazo)")
        mode = "portafolio" if ticker == planner.PORTFOLIO_MODE else "activo"
        return {"ticker": ticker, "findings": planner.new_findings(mode, ticker), "plan_log": log_}

    def planificar(state: AgentState) -> dict:
        ticker = state["ticker"]
        tasks = planner.initial_plan(state["question"], ticker, ctx.client["holdings"])
        if ticker is None:
            # Sin activo: solo se puede guardar una preferencia (si la hay)
            tasks = [t for t in tasks if t["herramienta"] == "guardar_preferencia"]
        return {"tasks": tasks, "initial_tasks": copy.deepcopy(tasks)}

    def _call_llm(messages: list[AnyMessage], cfg: RunnableConfig) -> tuple[AIMessage, dict]:
        try:
            return router.invoke(_masked(messages), cfg)
        except ProviderError as exc:
            # Ni siquiera el modo degradado esta en la cadena: se cierra igual
            log.error("llm_sin_proveedor", extra={"evento": "llm_sin_proveedor", "detalle": exc.detail})
            return AIMessage(content=""), {"proveedor": None, "error": exc.detail, "fallos": [], "degradado": True,
                                           "ms": 0, "tokens_entrada": 0, "tokens_salida": 0, "tool_calls": []}

    def agente(state: AgentState, config: RunnableConfig) -> dict:
        findings = state["findings"]
        events = list(state.get("events", []))
        calls = list(state.get("llm_calls", []))
        if state["steps"] >= settings.MAX_AGENT_STEPS:
            events.append({"tipo": "limite_de_pasos", "detalle": f"{settings.MAX_AGENT_STEPS} pasos"})
            return {"messages": [AIMessage(content=compose_answer(findings))], "events": events}
        risk = ctx.client["risk_profile"]
        system = SystemMessage(content=SYSTEM_PROMPT.format(
            client_name=pseudonym(ctx.client_id),  # el LLM externo no necesita el nombre real
            risk_category=risk["category"],
            risk_tolerance=risk["max_drawdown_tolerance_pct"],
            scenario=ctx.scenario,
            plan=planner.render_plan(state["tasks"]) or "(sin tareas)",
            findings=json.dumps(findings, ensure_ascii=False),
        ))
        if settings.IMPROVEMENTS_ENABLED:
            # Mejora EP3: el analisis mostro respuestas prematuras con tareas
            # pendientes; el estado del plan se hace explicito al final.
            pending_tasks = [t for t in state["tasks"] if t["estado"] == planner.PENDING]
            nxt = planner.next_task(state["tasks"])
            status = (f"\nESTADO: quedan {len(pending_tasks)} tareas pendientes. La siguiente es {nxt['id']} "
                      f"{nxt['herramienta']}. NO respondas al cliente hasta que queden 0."
                      if nxt else "\nESTADO: quedan 0 tareas pendientes. Responde ahora al cliente (regla 8).")
            system = SystemMessage(content=system.content + status)
        start = state["turn_start"]
        history = [system] + _previous_turns(state["messages"][:start]) + state["messages"][start:]
        response, info = _call_llm(history, config)
        info["paso"] = state["steps"] + 1
        calls.append(info)

        pending = planner.next_task(state["tasks"])
        if not response.tool_calls and pending is not None and info.get("proveedor"):
            # El LLM quiso responder con tareas pendientes: un recordatorio
            events.append({"tipo": "respuesta_prematura", "detalle": f"quedaba {pending['id']} {pending['herramienta']}"})
            reminder = HumanMessage(content=(
                f"[sistema] Aun queda la tarea {pending['id']} del PLAN: llama a {pending['herramienta']} "
                f"con {json.dumps(pending['args'], ensure_ascii=False)} antes de responder."))
            response, info = _call_llm(history + [reminder], config)
            info["paso"] = state["steps"] + 1
            info["reintento_por_plan"] = True
            calls.append(info)

        if not response.tool_calls and not (response.content or "").strip():
            events.append({"tipo": "respuesta_vacia", "detalle": "el LLM no devolvio texto ni herramientas"})
            response = AIMessage(content=compose_answer(findings))

        known = {t.name for t in tools}
        bad = [tc["name"] for tc in response.tool_calls if tc["name"] not in known]
        if bad:
            events.append({"tipo": "herramienta_inexistente", "detalle": ", ".join(bad)})
        return {"messages": [response], "steps": state["steps"] + 1, "llm_calls": calls, "events": events}

    def replanificar(state: AgentState) -> dict:
        tasks = copy.deepcopy(state["tasks"])
        findings = copy.deepcopy(state["findings"])
        log_ = list(state["plan_log"])
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
            log_ += decisions
            trace.append({
                "herramienta": call["name"],
                "args": call["args"],
                "resultado": result,
                "decisiones": decisions,
                "plan": copy.deepcopy(tasks),
            })
        return {"tasks": tasks, "findings": findings, "plan_log": log_, "trace": trace}

    def validar(state: AgentState) -> dict:
        last = state["messages"][-1]
        answer = last.content or ""
        findings = state["findings"]
        violations = guardrails.validate_output(answer, findings)
        result = {"violaciones": violations, "intervino": False,
                  "accion_llm": classify_action(answer), "accion_reglas": None}
        if findings["ticker"] is not None:
            result["accion_reglas"] = guardrails.expected_category(findings)
        if violations:
            log.warning("guardrail_violacion", extra={"evento": "guardrail_violacion", "violaciones": violations,
                                                      "activo_guardrail": config.GUARDRAIL_ENABLED,
                                                      "cliente": pseudonym(ctx.client_id)})
        if violations and config.GUARDRAIL_ENABLED:
            result["intervino"] = True
            answer = (compose_answer(findings) + "\n(Respuesta corregida por el control de reglas: "
                      + ", ".join(violations) + ".)")
        if findings["ticker"] is not None and not findings["error"] and guardrails.DISCLAIMER not in answer:
            answer = answer.rstrip() + "\n" + guardrails.DISCLAIMER
        return {"messages": [AIMessage(content=answer, id=last.id)], "guardrail": result}

    def persistir(state: AgentState) -> dict:
        findings = state["findings"]
        ticker = state["ticker"]
        if ticker and not findings["error"]:
            answer = state["messages"][-1].content
            match = _ACTION_RE.search(answer + "\n")
            args = (ctx.client_id, "interaccion", f"Pregunta: {state['question']} | Respuesta: {answer}")
            kwargs = {"ticker": ticker,
                      "metadata": {"accion": match.group(1) if match else None, "escenario": ctx.scenario}}
            if settings.IMPROVEMENTS_ENABLED:
                # Mejora EP3: el embedding (1-2 s en CPU) se calcula en segundo
                # plano y sobre un resumen corto, no sobre la respuesta completa
                summary = f"{state['question']} | {ticker}: {kwargs['metadata']['accion']}"
                ctx.memory.remember_async(*args, embed_from=summary, **kwargs)
            else:
                ctx.memory.remember(*args, **kwargs)
        return {}

    def route_after_security(state: AgentState) -> str:
        return "bloquear" if state["security"]["bloqueado"] else "interpretar"

    def route_after_agent(state: AgentState) -> str:
        last = state["messages"][-1]
        return "herramientas" if isinstance(last, AIMessage) and last.tool_calls else "validar"

    graph = StateGraph(AgentState)
    graph.add_node("seguridad", seguridad)
    graph.add_node("bloquear", bloquear)
    graph.add_node("interpretar", interpretar)
    graph.add_node("planificar", planificar)
    graph.add_node("agente", agente)
    graph.add_node("herramientas", ToolNode(tools))
    graph.add_node("replanificar", replanificar)
    graph.add_node("validar", validar)
    graph.add_node("persistir", persistir)

    graph.add_edge(START, "seguridad")
    graph.add_conditional_edges("seguridad", route_after_security, ["bloquear", "interpretar"])
    graph.add_edge("bloquear", END)
    graph.add_edge("interpretar", "planificar")
    graph.add_edge("planificar", "agente")
    graph.add_conditional_edges("agente", route_after_agent, ["herramientas", "validar"])
    graph.add_edge("herramientas", "replanificar")
    graph.add_edge("replanificar", "agente")
    graph.add_edge("validar", "persistir")
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
        chain: list[str] | None = None,
        trace_store: TraceStore | None = None,
    ):
        output_dir = Path(output_dir or config.OUTPUT_DIR)
        self.ctx = AgentContext(
            client_id=client_id,
            memory=memory or LongTermMemory(),
            output_dir=output_dir,
            scenario=scenario,
        )
        self.tools = build_tools(self.ctx)
        self.router = LLMRouter(self.tools, chain=chain, model=model)
        output_dir.mkdir(parents=True, exist_ok=True)
        # Memoria de corto plazo persistente: sobrevive a reinicios del proceso
        self._checkpoint_conn = sqlite3.connect(str(output_dir / config.CHECKPOINT_DB_NAME), check_same_thread=False)
        self.graph = build_graph(self.ctx, self.router, self.tools).compile(
            checkpointer=SqliteSaver(self._checkpoint_conn)
        )
        self.trace_store = trace_store or TraceStore(
            output_dir / "observabilidad" if output_dir != config.OUTPUT_DIR else None)
        setup_logging(self.trace_store.directory)

    def set_scenario(self, scenario: str) -> None:
        self.ctx.set_scenario(scenario)

    def _thread(self, thread_id: str) -> str:
        # El archivo de checkpoints es compartido por todos los clientes
        return f"{self.ctx.client_id}::{thread_id}"

    def ask(self, question: str, thread_id: str = "conversacion-1", tags: dict | None = None) -> AgentResult:
        trace_id = uuid.uuid4().hex[:12]
        collector = TraceCollector()
        started = time.perf_counter()
        error: BaseException | None = None
        state: dict = {}
        with ResourceMonitor() as resources:
            try:
                state = self.graph.invoke(
                    {"messages": [HumanMessage(content=question)]},
                    config={"configurable": {"thread_id": self._thread(thread_id)},
                            "recursion_limit": 4 * config.MAX_AGENT_STEPS + 10,
                            "callbacks": [collector], "run_name": "turno_agente"},
                )
            except Exception as exc:  # se registra la traza y se propaga
                error = exc
        latency = round((time.perf_counter() - started) * 1000, 1)
        record = self._trace_record(trace_id, question, thread_id, state, collector.finish(),
                                    resources.summary, latency, error, tags or {})
        self.trace_store.append(record)
        log_fn = log.error if record["estado"] == "error" else log.info
        log_fn("turno_completado", extra={k: record[k] for k in (
            "trace_id", "cliente", "escenario", "estado", "accion", "proveedor", "latencia_ms", "degradado")})
        if error is not None:
            raise error

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
            ticker=state.get("ticker"),
            plan_inicial=state.get("initial_tasks", []),
            plan_final=state.get("tasks", []),
            plan_log=state.get("plan_log", []),
            herramientas=executed,
            pasos=state.get("trace", []),
            findings=state.get("findings", {}),
            accion_categoria=record["accion"],
            proveedor=record["proveedor"],
            degradado=record["degradado"],
            guardrail=state.get("guardrail", {}),
            seguridad=state.get("security", {}),
            traza_id=trace_id,
            latencia_ms=latency,
        )

    # ------------------------------------------------------------ traza del turno
    def _trace_record(self, trace_id: str, question: str, thread_id: str, state: dict, spans: list[dict],
                      resources: dict, latency: float, error: BaseException | None, tags: dict) -> dict:
        calls = state.get("llm_calls", [])
        security = state.get("security", {})
        guard = state.get("guardrail", {})
        findings = state.get("findings") or {}
        messages = state.get("messages", [])
        answer = messages[-1].content if messages else ""
        tasks = state.get("tasks", [])
        plan_log = state.get("plan_log", [])

        node_ms: dict[str, float] = {}
        for s in spans:
            if s["tipo"] == "nodo":
                node_ms[s["nombre"]] = round(node_ms.get(s["nombre"], 0) + s["dur_ms"], 1)
        tool_spans = [s for s in spans if s["tipo"] == "herramienta"]
        providers = [c["proveedor"] for c in calls if c.get("proveedor")]
        failures = [f for c in calls for f in c.get("fallos", [])]
        events = list(state.get("events", []))
        events += [{"tipo": "accion_no_planificada", "detalle": e} for e in plan_log if e.startswith("Accion no planificada")]
        events += [{"tipo": "herramienta_fallida", "detalle": f"{s['nombre']}: {s.get('error', '')}"}
                   for s in tool_spans if s["estado"] == "error"]
        events += [{"tipo": f"llm_{f['tipo']}", "detalle": f"{f['proveedor']}: {f.get('detalle', '')}"[:200]}
                   for f in failures]

        if error is not None:
            status = "error"
        elif security.get("bloqueado"):
            status = "bloqueado"
        elif any(c.get("degradado") for c in calls):
            status = "degradado"
        else:
            status = "ok"

        return {
            "trace_id": trace_id,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "cliente": pseudonym(self.ctx.client_id),
            "perfil": self.ctx.client["risk_profile"]["category"],
            "escenario": self.ctx.scenario,
            "hilo": pseudonym(self._thread(thread_id))[4:],
            "pregunta": mask_pii(question),
            "respuesta": mask_pii(answer)[:800],
            "ticker": state.get("ticker"),
            "accion": "bloqueado" if security.get("bloqueado") else classify_action(answer),
            "estado": status,
            "error": mask_pii(f"{type(error).__name__}: {error}")[:300] if error else None,
            "cadena_llm": self.router.chain,
            "proveedor": providers[-1] if providers else None,
            "modelo": next((c.get("modelo") for c in reversed(calls) if c.get("modelo")), None),
            "degradado": any(c.get("degradado") for c in calls),
            "latencia_ms": latency,
            "llm_ms": round(sum(c.get("ms", 0) for c in calls), 1),
            "espera_cuota_ms": round(sum(c.get("espera_cuota_ms", 0) for c in calls), 1),
            "herramientas_ms": round(sum(s["dur_ms"] for s in tool_spans), 1),
            "nodos_ms": node_ms,
            "llm_llamadas": len(calls),
            "llm_detalle": calls,
            "tokens_entrada": sum(c.get("tokens_entrada", 0) for c in calls),
            "tokens_salida": sum(c.get("tokens_salida", 0) for c in calls),
            "herramientas": [{"nombre": s["nombre"], "ms": s["dur_ms"], "estado": s["estado"]} for s in tool_spans],
            "pasos": state.get("steps", 0),
            "plan_tareas": len(tasks),
            "plan_pendientes": sum(1 for t in tasks if t["estado"] == planner.PENDING),
            "plan_canceladas": sum(1 for t in tasks if t["estado"] == planner.CANCELLED),
            "replanificaciones": [e.split(":")[0] for e in plan_log if re.match(r"R\d", e)],
            "datos_confiables": findings.get("datos_confiables"),
            "alertas": len(findings.get("alertas", []) or []),
            "guardrail": guard,
            "seguridad": {"inyeccion": security.get("inyeccion", []), "pii_entrada": security.get("pii_entrada", [])},
            "eventos": events,
            "recursos": resources,
            "spans": spans,
            **({"eval": tags} if tags else {}),
        }
