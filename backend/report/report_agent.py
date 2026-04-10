import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.utils.llm_client import call_llm_json
from backend.utils.graph_utils import get_most_influential
import networkx as nx

async def generate_report(
    topic: str,
    simulation_id: str,
    rounds: list[dict],
    final_agents: list[dict],
    G: nx.DiGraph
) -> dict:
    """
    God's Eye View report agent.
    Has access to the full simulation transcript and knowledge graph.
    Synthesizes insights a single agent could never see.
    """

    print(f"[ReportAgent] Generating God's Eye View for simulation {simulation_id}")

    # ── Build full debate transcript ──────────────────────────────
    transcript = []
    for round_data in rounds:
        for agent in round_data["agents"]:
            transcript.append(
                f"Round {round_data['round']} | {agent['name']} ({agent['stance']}) "
                f"score={agent['score']} delta={agent['opinion_delta']}: {agent['opinion']}"
            )
    transcript_str = "\n".join(transcript)

    # ── Find who shifted and who held ────────────────────────────
    first_round_agents = {
        a["id"]: a for a in rounds[0]["agents"]
    } if rounds else {}

    agents_shifted = []
    agents_held = []

    for agent in final_agents:
        agent_id = agent["id"]
        first_state = first_round_agents.get(agent_id)
        
        if not first_state:
            # fallback — use agent's own shift flag from debate engine
            shifted = agent.get("shifted", False)
            initial_stance = agent["stance"]
        else:
            initial_stance = first_state["stance"]
            final_stance = agent["stance"]
            # check both stance change AND debate engine shift flag
            shifted = (initial_stance != final_stance) or agent.get("shifted", False)

        summary = {
            "agent_id": agent_id,
            "name": agent["name"],
            "shifted": shifted,
            "initial_stance": initial_stance,
            "final_stance": final_stance,
            "initial_score": first_state["score"],
            "final_score": agent["score"],
            "total_delta": abs(agent["score"] - first_state["score"]),
            "key_moment": agent.get("shift_reason", "held firm throughout")
        }

        if shifted:
            agents_shifted.append(summary)
        else:
            agents_held.append(summary)

    # ── Find decisive arguments ───────────────────────────────────
    # An argument is decisive if it caused multiple agents to shift
    argument_influence = {}
    for agent in final_agents:
        if agent.get("shifted") and agent.get("last_argument"):
            key = agent.get("last_argument", "")[:100]
            if key not in argument_influence:
                argument_influence[key] = {
                    "argument": agent.get("last_argument", ""),
                    "influenced_agents": [],
                    "evidence_used": agent.get("key_evidence_used", [])
                }
            argument_influence[key]["influenced_agents"].append(agent["id"])

    decisive_arguments = [
        {
            "agent_id": final_agents[0]["id"] if final_agents else "unknown",
            "argument": v["argument"],
            "influenced_agents": v["influenced_agents"],
            "evidence_used": v["evidence_used"]
        }
        for v in argument_influence.values()
        if len(v["influenced_agents"]) >= 1
    ][:5]

    # ── Graph insights ────────────────────────────────────────────
    top_entities = get_most_influential(G, top_n=3)
    graph_context = "\n".join([
        f"- {e['name']} (influence: {e['influence_score']:.3f}, cited {e['citations']}x)"
        for e in top_entities
    ])

    # ── LLM synthesizes the God's Eye View ───────────────────────
    system = """You are the God's Eye View analyst for a multi-agent debate simulation.
You have seen the full debate transcript and all agent positions.
Your job is to synthesize insights that no single agent could see.
Respond in valid JSON only."""

    prompt = f"""Analyze this complete debate simulation and generate a God's Eye View report.

Topic: {topic}
Total agents: {len(final_agents)}
Agents who shifted opinion: {len(agents_shifted)}
Agents who held firm: {len(agents_held)}

Most influential knowledge graph entities:
{graph_context}

Full debate transcript:
{transcript_str[:1500]}

Generate a God's Eye View synthesis in this exact JSON format:
{{
    "summary": "2-3 sentence executive summary of what happened in the debate",
    "predicted_trajectory": "Based on the debate dynamics, what is the predicted real-world trajectory of public opinion on this topic? Be specific and cite the dominant arguments.",
    "dominant_narrative": "What was the strongest narrative that emerged?",
    "key_turning_point": "What was the single moment or argument that changed the most minds?",
    "consensus_level": "high/medium/low",
    "actionable_insight": "One specific actionable insight for a decision maker reading this report"
}}"""

    try:
        result = await call_llm_json(prompt, system)
        synthesis = json.loads(result)
    except Exception as e:
        print(f"[ReportAgent] LLM synthesis error: {e}")
        synthesis = {
            "summary": "Debate completed successfully.",
            "predicted_trajectory": "Unable to generate trajectory.",
            "dominant_narrative": "",
            "key_turning_point": "",
            "consensus_level": "medium",
            "actionable_insight": ""
        }

    # ── Calculate sentiment per round ─────────────────────────────
    sentiment_ticks = []
    for round_data in rounds:
        agents_in_round = round_data["agents"]
        total = len(agents_in_round)
        if total == 0:
            continue

        positive = sum(1 for a in agents_in_round if a["stance"] == "for") / total
        negative = sum(1 for a in agents_in_round if a["stance"] == "against") / total
        neutral = sum(1 for a in agents_in_round if a["stance"] == "neutral") / total

        sentiment_ticks.append({
            "tick": round_data["round"],
            "positive": round(positive, 2),
            "neutral": round(neutral, 2),
            "negative": round(negative, 2)
        })

    # ── Assemble final report ─────────────────────────────────────
    report = {
        "simulation_id": simulation_id,
        "topic": topic,
        "summary": synthesis.get("summary", ""),
        "predicted_trajectory": synthesis.get("predicted_trajectory", ""),
        "dominant_narrative": synthesis.get("dominant_narrative", ""),
        "key_turning_point": synthesis.get("key_turning_point", ""),
        "consensus_level": synthesis.get("consensus_level", "medium"),
        "actionable_insight": synthesis.get("actionable_insight", ""),
        "agents_shifted": len(agents_shifted),
        "agents_held": len(agents_held),
        "decisive_arguments": decisive_arguments,
        "agent_summaries": [
            {
                "agent_id": a["agent_id"],
                "name": a["name"],
                "shifted": a["shifted"],
                "final_stance": a["final_stance"],
                "key_moment": a["key_moment"]
            }
            for a in agents_shifted + agents_held
        ],
        "sentiment_history": {
            "simulation_id": simulation_id,
            "ticks": sentiment_ticks
        }
    }

    print(f"[ReportAgent] Report complete. "
          f"{len(agents_shifted)} shifted, {len(agents_held)} held.")

    return report