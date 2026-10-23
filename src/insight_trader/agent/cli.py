"""CLI del agente (demo en vivo).

Uso:
    python -m insight_trader.agent.cli --client valentina_rojas "Que hago con TSLA?"
    python -m insight_trader.agent.cli --client constanza_fuentes          # modo conversacion

En modo conversacion todos los turnos comparten el mismo thread_id
(memoria de corto plazo). Comandos: /escenario <normal|shock|datos_desactualizados>,
/memoria, /salir.
"""
from __future__ import annotations

import argparse

from insight_trader import config
from insight_trader.agent.environment import SCENARIOS
from insight_trader.agent.graph import AgentResult, InsightTraderAgent
from insight_trader.agent.planner import render_plan


def print_result(result: AgentResult, verbose: bool = True) -> None:
    if verbose:
        print("\n== Plan inicial ==")
        print(render_plan(result.plan_inicial) or "(sin tareas)")
        print("\n== Herramientas ejecutadas (en orden) ==")
        for i, call in enumerate(result.herramientas, 1):
            print(f"{i:>2}. {call}")
        print("\n== Decisiones de re-planificacion ==")
        print("\n".join(f"- {entry}" for entry in result.plan_log) or "- (el plan inicial no requirio ajustes)")
        print("\n== Plan final ==")
        print(render_plan(result.plan_final) or "(sin tareas)")
    print("\n== Respuesta del agente ==")
    print(result.respuesta)


def main() -> None:
    parser = argparse.ArgumentParser(description="Insight Trader - agente copiloto de inversiones (EP2)")
    parser.add_argument("question", nargs="?", help="Pregunta; si se omite se abre una conversacion")
    parser.add_argument("--client", default=config.DEFAULT_CLIENT_ID, choices=config.list_client_ids())
    parser.add_argument("--escenario", default="normal", choices=SCENARIOS)
    parser.add_argument("--thread", default="conversacion-1", help="Id de la conversacion (memoria corto plazo)")
    parser.add_argument("--reset-memoria", action="store_true", help="Borra la memoria de largo plazo del cliente")
    parser.add_argument("--breve", action="store_true", help="Muestra solo la respuesta, sin la traza del plan")
    args = parser.parse_args()

    agent = InsightTraderAgent(client_id=args.client, scenario=args.escenario)
    if args.reset_memoria:
        agent.ctx.memory.clear(args.client)
    print(f"Cliente: {agent.ctx.client['client_name']} | escenario: {args.escenario} | "
          f"recuerdos en memoria de largo plazo: {agent.ctx.memory.count(args.client)}")

    if args.question:
        print_result(agent.ask(args.question, args.thread), verbose=not args.breve)
        return

    print("Escribe tu pregunta (/escenario <nombre>, /memoria, /salir).")
    while True:
        try:
            question = input("\nTu> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        if question == "/salir":
            break
        if question.startswith("/escenario"):
            parts = question.split()
            if len(parts) == 2 and parts[1] in SCENARIOS:
                agent.set_scenario(parts[1])
                print(f"Entorno de mercado cambiado a '{parts[1]}'")
            else:
                print(f"Uso: /escenario <{'|'.join(SCENARIOS)}>")
            continue
        if question == "/memoria":
            for item in agent.ctx.memory.search(args.client, "recomendacion preferencia", top_k=10):
                print(f"- [{item.kind}] {item.ticker or '-'} {item.created_at}: {item.content.replace(chr(10), ' ')[:140]}")
            continue
        print_result(agent.ask(question, args.thread), verbose=not args.breve)


if __name__ == "__main__":
    main()
