"""API HTTP minima para la vista web "Agente en vivo" (web-react).

Usa solo la biblioteca estandar (`http.server`) para no agregar
dependencias: la vista React la consume via el proxy de Vite (/api).

    python -m insight_trader.agent.server            # http://localhost:8000

Endpoints:
    GET  /api/health
    GET  /api/clients                  -> clientes, perfil, posiciones, recuerdos
    GET  /api/catalog                  -> activos y perfiles para crear clientes
    GET  /api/market?scenario=shock    -> metricas del escenario e impacto en clientes
    GET  /api/market/real              -> referencia de mercado real (Yahoo Finance)
    GET  /api/recommendations?scenario=shock -> accion sugerida por posicion y cliente
    GET  /api/observability            -> metricas, hallazgos y trazas (EP3)
    POST /api/clients {client_name, risk_category, ...}  -> crea un cliente
    POST /api/clients/delete {client_id}                  -> elimina un cliente creado
    POST /api/ask    {client_id, question, thread_id, scenario}
    POST /api/reset  {client_id}       -> borra la memoria de largo plazo
"""
from __future__ import annotations

import argparse
import json
import threading
from urllib.parse import parse_qs, urlsplit
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from insight_trader import config
from insight_trader.agent import clients as client_store
from insight_trader.agent.environment import SCENARIOS
from insight_trader.agent.graph import AgentResult, InsightTraderAgent
from insight_trader.agent.market_view import real_market, scenario_snapshot
from insight_trader.agent.memory import LongTermMemory
from insight_trader.agent.recommendations import recommendations
from insight_trader.agent.tools import TOOL_GROUPS
from insight_trader.observability.report import dashboard_payload
from insight_trader.observability.store import TraceStore

TOOL_TYPE = {name: group for group, names in TOOL_GROUPS.items() for name in names}


def client_info(agent: InsightTraderAgent) -> dict:
    client = agent.ctx.client
    risk = client["risk_profile"]
    return {
        "client_id": agent.ctx.client_id,
        "client_name": client["client_name"],
        "risk_category": risk["category"],
        "risk_tolerance": risk["max_drawdown_tolerance_pct"],
        "investment_horizon_years": risk["investment_horizon_years"],
        "notes": risk["notes"],
        "holdings": [
            {"ticker": h["ticker"], "name": h["name"], "weight": h["current_weight_pct"], "asset_class": h["asset_class"]}
            for h in client["holdings"]
        ],
        "memory_count": agent.ctx.memory.count(agent.ctx.client_id),
        "custom": config.is_custom_client(agent.ctx.client_id),
    }


def serialize_result(result: AgentResult, scenario: str, question: str) -> dict:
    data = asdict(result)
    for step in data["pasos"]:
        step["tipo"] = TOOL_TYPE.get(step["herramienta"], "otro")
    findings = data.pop("findings")
    data.update({
        "pregunta": question,
        "escenario": scenario,
        "alertas": findings["alertas"],
        "informe": findings["informe"],
        "datos_confiables": findings["datos_confiables"],
        "restricciones": findings["restricciones"],
    })
    return data


class AgentService:
    """Un agente por cliente, compartiendo la memoria de largo plazo."""

    def __init__(self, memory: LongTermMemory | None = None):
        self._memory = memory or LongTermMemory()
        self._agents: dict[str, InsightTraderAgent] = {}
        self._lock = threading.Lock()

    def agent(self, client_id: str) -> InsightTraderAgent:
        if client_id not in config.list_client_ids():
            raise ValueError(f"Cliente desconocido: {client_id}")
        if client_id not in self._agents:
            self._agents[client_id] = InsightTraderAgent(client_id, memory=self._memory)
        return self._agents[client_id]

    def clients(self) -> list[dict]:
        with self._lock:
            return [client_info(self.agent(cid)) for cid in config.list_client_ids()]

    def ask(self, client_id: str, question: str, thread_id: str, scenario: str) -> dict:
        if scenario not in SCENARIOS:
            raise ValueError(f"Escenario desconocido: {scenario}")
        with self._lock:
            agent = self.agent(client_id)
            if agent.ctx.scenario != scenario:
                agent.set_scenario(scenario)
            result = agent.ask(question, thread_id)
            return {"resultado": serialize_result(result, scenario, question), "cliente": client_info(agent)}

    def create_client(self, data: dict) -> dict:
        with self._lock:
            client_id = client_store.create_client(data)
            return client_info(self.agent(client_id))

    def delete_client(self, client_id: str) -> dict:
        with self._lock:
            client_store.delete_client(client_id)
            self._memory.clear(client_id)
            self._agents.pop(client_id, None)
            return {"eliminado": client_id}

    def recommendations(self, scenario: str) -> dict:
        with self._lock:
            return recommendations(scenario, self._memory)

    def reset(self, client_id: str) -> dict:
        with self._lock:
            self._memory.clear(client_id)
            return client_info(self.agent(client_id))


def make_handler(service: AgentService):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: dict | list) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):  # noqa: N802 (preflight CORS)
            self._send(204, {})

        def do_GET(self):  # noqa: N802
            url = urlsplit(self.path)
            if url.path == "/api/market":
                scenario = parse_qs(url.query).get("scenario", ["normal"])[0]
                if scenario not in SCENARIOS:
                    self._send(400, {"error": f"Escenario desconocido: {scenario}"})
                else:
                    self._send(200, scenario_snapshot(scenario))
            elif url.path == "/api/recommendations":
                scenario = parse_qs(url.query).get("scenario", ["normal"])[0]
                if scenario not in SCENARIOS:
                    self._send(400, {"error": f"Escenario desconocido: {scenario}"})
                else:
                    self._send(200, service.recommendations(scenario))
            elif url.path == "/api/market/real":
                self._send(200, real_market())
            elif url.path == "/api/observability":
                self._send(200, dashboard_payload(TraceStore().load()))
            elif self.path == "/api/health":
                self._send(200, {"ok": True, "escenarios": list(SCENARIOS)})
            elif self.path == "/api/clients":
                self._send(200, service.clients())
            elif self.path == "/api/catalog":
                self._send(200, {
                    "activos": client_store.asset_catalog(),
                    "perfiles": list(client_store.RISK_CATEGORIES),
                    "tolerancia_sugerida": client_store.DEFAULT_TOLERANCE,
                })
            else:
                self._send(404, {"error": "ruta no encontrada"})

        def do_POST(self):  # noqa: N802
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/api/ask":
                    question = (body.get("question") or "").strip()
                    if not question:
                        raise ValueError("La pregunta no puede estar vacia")
                    self._send(200, service.ask(
                        body.get("client_id", config.DEFAULT_CLIENT_ID),
                        question,
                        body.get("thread_id", "web"),
                        body.get("scenario", "normal"),
                    ))
                elif self.path == "/api/clients":
                    self._send(201, service.create_client(body))
                elif self.path == "/api/clients/delete":
                    self._send(200, service.delete_client(body.get("client_id", "")))
                elif self.path == "/api/reset":
                    self._send(200, service.reset(body.get("client_id", config.DEFAULT_CLIENT_ID)))
                else:
                    self._send(404, {"error": "ruta no encontrada"})
            except ValueError as exc:
                self._send(400, {"error": str(exc)})

        def log_message(self, fmt, *args):
            print(f"[api] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="API del agente Insight Trader para la vista web")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(AgentService()))
    print(f"Agente Insight Trader escuchando en http://localhost:{args.port}/api (Ctrl+C para detener)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
