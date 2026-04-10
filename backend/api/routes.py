import asyncio
import uuid
import json
from flask import Blueprint, request, jsonify
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.ingestion.ingestor import ingest
from backend.ingestion.graph_builder import build_graph, get_graph_summary
from backend.agents.persona_generator import generate_personas
from backend.agents.debate_engine import run_debate
from backend.report.report_agent import generate_report

api = Blueprint("api", __name__)

# ── In-memory store (Phase 1) ─────────────────────────────────────
# Stores active simulations by simulation_id
# In Phase 2 we replace this with a proper database
simulations = {}

# ── Helper ────────────────────────────────────────────────────────
def run_async(coro):
    """Run async functions from Flask's sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# ── 1. Start simulation ───────────────────────────────────────────
@api.route("/api/simulation/start", methods=["POST"])
def start_simulation():
    try:
        body = request.get_json()
        topic = body.get("topic")
        num_agents = body.get("num_agents", 20)
        num_rounds = body.get("num_rounds", 3)
        pdf_paths = body.get("uploads", [])

        if not topic:
            return jsonify({"error": "topic is required"}), 400

        simulation_id = f"sim_{uuid.uuid4().hex[:8]}"
        print(f"\n[API] Starting simulation {simulation_id} on: {topic}")

        # Step 1 — Ingest real world data
        chunks = run_async(ingest(topic, pdf_paths))

        # Step 2 — Build knowledge graph
        G = run_async(build_graph(chunks))
        graph_summary = get_graph_summary(G)

        # Step 3 — Generate personas grounded in graph
        agents = run_async(generate_personas(topic, G, num_agents))

        # Step 4 — Run the debate
        debate_result = run_async(run_debate(topic, agents, G, num_rounds))

        # Step 5 — Generate God's Eye View report
        report = run_async(generate_report(
            topic=topic,
            simulation_id=simulation_id,
            rounds=debate_result["rounds"],
            final_agents=debate_result["final_agents"],
            G=G
        ))

        # Store everything
        simulations[simulation_id] = {
            "simulation_id": simulation_id,
            "topic": topic,
            "status": "completed",
            "agents_created": len(agents),
            "graph_summary": graph_summary,
            "rounds": debate_result["rounds"],
            "final_agents": debate_result["final_agents"],
            "report": report
        }

        return jsonify({
            "simulation_id": simulation_id,
            "status": "completed",
            "agents_created": len(agents),
            "graph_summary": graph_summary
        }), 200

    except Exception as e:
        print(f"[API] Error: {e}")
        return jsonify({"error": str(e)}), 500


# ── 2. Get debate rounds ──────────────────────────────────────────
@api.route("/api/simulation/<simulation_id>/debate", methods=["GET"])
def get_debate(simulation_id):
    sim = simulations.get(simulation_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    return jsonify({
        "simulation_id": simulation_id,
        "rounds": sim["rounds"]
    }), 200


# ── 3. Get agent memory ───────────────────────────────────────────
@api.route("/api/agent/<agent_id>/memory", methods=["GET"])
def get_agent_memory(agent_id):
    # Search all simulations for this agent
    memory = []
    for sim_id, sim in simulations.items():
        for agent in sim.get("final_agents", []):
            if agent["id"] == agent_id:
                memory.append({
                    "simulation_id": sim_id,
                    "date": "2026-04-10",
                    "topic": sim["topic"],
                    "final_opinion": agent["opinion"],
                    "final_score": agent["score"],
                    "shifted": agent.get("shifted", False)
                })

    if not memory:
        return jsonify({"error": "agent not found"}), 404

    agent_data = None
    for sim in simulations.values():
        for agent in sim.get("final_agents", []):
            if agent["id"] == agent_id:
                agent_data = agent
                break

    return jsonify({
        "agent_id": agent_id,
        "name": agent_data["name"],
        "persona": agent_data["persona"],
        "memory": memory
    }), 200


# ── 4. Inject live event ──────────────────────────────────────────
@api.route("/api/inject", methods=["POST"])
def inject_event():
    try:
        body = request.get_json()
        simulation_id = body.get("simulation_id")
        event = body.get("event")

        sim = simulations.get(simulation_id)
        if not sim:
            return jsonify({"error": "simulation not found"}), 404

        if not event:
            return jsonify({"error": "event is required"}), 400

        final_agents = sim["final_agents"]
        current_tick = len(sim["rounds"]) + 1

        # Inject the event as a new debate round
        from backend.utils.graph_utils import query_graph
        from backend.agents.debate_engine import run_debate_round

        # Temporarily add the event as a node concept
        # In Phase 2 this re-ingests and updates the graph
        reactions = []
        for agent in final_agents:
            old_opinion = agent["opinion"]
            old_score = agent["score"]

            reactions.append({
                "agent_id": agent["id"],
                "name": agent["name"],
                "opinion_before": old_opinion,
                "opinion_after": f"Considering: {event}. {old_opinion}",
                "delta": 0.0,
                "shifted": False
            })

        return jsonify({
            "injected_at_tick": current_tick,
            "reactions": reactions
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 5. Branch simulation ──────────────────────────────────────────
@api.route("/api/branch", methods=["POST"])
def branch_simulation():
    try:
        body = request.get_json()
        simulation_id = body.get("simulation_id")
        from_tick = body.get("from_tick")

        sim = simulations.get(simulation_id)
        if not sim:
            return jsonify({"error": "simulation not found"}), 404

        branch_id = f"branch_{uuid.uuid4().hex[:8]}"

        # Clone state up to from_tick
        branched_rounds = sim["rounds"][:from_tick]
        branched_agents = branched_rounds[-1]["agents"] if branched_rounds else []

        simulations[branch_id] = {
            "simulation_id": branch_id,
            "topic": sim["topic"],
            "status": "running",
            "agents_created": len(branched_agents),
            "rounds": branched_rounds,
            "final_agents": branched_agents,
            "parent_simulation_id": simulation_id,
            "branched_at_tick": from_tick,
            "report": {}
        }

        return jsonify({
            "branch_id": branch_id,
            "parent_simulation_id": simulation_id,
            "branched_at_tick": from_tick,
            "status": "running"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── 6. Get report ─────────────────────────────────────────────────
@api.route("/api/report/<simulation_id>", methods=["GET"])
def get_report(simulation_id):
    sim = simulations.get(simulation_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    return jsonify(sim["report"]), 200


# ── 7. Get sentiment history ──────────────────────────────────────
@api.route("/api/sentiment/history/<simulation_id>", methods=["GET"])
def get_sentiment_history(simulation_id):
    sim = simulations.get(simulation_id)
    if not sim:
        return jsonify({"error": "simulation not found"}), 404

    return jsonify(
        sim["report"].get("sentiment_history", {
            "simulation_id": simulation_id,
            "ticks": []
        })
    ), 200