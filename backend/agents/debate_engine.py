import json
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.utils.llm_client import call_llm_json
from backend.utils.graph_utils import query_graph
import networkx as nx

async def run_single_agent_round(
    agent: dict,
    all_agents: list[dict],
    topic: str,
    G: nx.DiGraph,
    round_num: int
) -> dict:
    """
    Run a single agent through one debate round.
    Agent queries graph for evidence, reads opponents, decides to shift or hold.
    """

    # Step 1 — Agent pulls evidence from knowledge graph based on their beliefs
    keywords = agent["key_beliefs"] + agent["known_entities"]
    evidence = query_graph(G, keywords, top_n=5)

    evidence_context = "\n".join([
        f"- {e['name']}: {e['description'][:150]} [source: {e['source'][:60]}] (cited {e['citations']}x)"
        for e in evidence
    ])

    # Step 2 — Agent reads what opponents said last round
    opponents = [a for a in all_agents if a["id"] != agent["id"]]
    opponent_context = "\n".join([
        f"- {o['name']} ({o['stance']}): {o['opinion']}"
        for o in opponents[:5]  # cap at 5 opponents to keep context manageable
    ])

    system = """You are simulating a realistic human debater.
You are grounded in real evidence from a knowledge graph.
You must respond in valid JSON only."""

    prompt = f"""You are {agent['name']}, {agent['profession']} from {agent['location']}.
Your personality: {agent['persona']}
Your persuasion resistance: {agent['persuasion_resistance']} (0=easily convinced, 1=never convinced)

Topic being debated: {topic}
Current debate round: {round_num}

Your current position:
- Opinion: {agent['opinion']}
- Score: {agent['score']} (1=strongly against, 10=strongly for)
- Stance: {agent['stance']}

Evidence available to you from real sources:
{evidence_context}

What other debaters said this round:
{opponent_context}

Based on your personality, the evidence, and what others said:
1. Form your argument using specific evidence from the sources above
2. Decide if any opponent's argument genuinely moves you
3. Update your opinion and score accordingly

Your persuasion_resistance of {agent['persuasion_resistance']} means:
- Above 0.7: you rarely shift, need overwhelming evidence
- 0.4-0.7: you shift if the argument is backed by strong evidence  
- Below 0.4: you are open minded and shift more easily

Respond in this exact JSON format:
{{
    "argument": "your argument this round, citing specific sources",
    "responding_to": "which opponent you are responding to, or null",
    "new_opinion": "your updated opinion in 2 sentences",
    "new_score": 6.5,
    "new_stance": "for/against/neutral",
    "shifted": true,
    "shift_reason": "why you shifted or why you held firm",
    "key_evidence_used": ["evidence point 1", "evidence point 2"]
}}

Rules:
- new_score must be between 1.0 and 10.0
- Be realistic — don't shift dramatically in one round
- If you shift, the shift should be proportional to your persuasion_resistance
- Always cite specific evidence from the sources provided above"""

    try:
        result = await call_llm_json(prompt, system)
        response = json.loads(result)

        # Calculate opinion delta
        old_score = agent["score"]
        new_score = float(response.get("new_score", old_score))
        opinion_delta = abs(new_score - old_score)

        # Update agent state
        updated_agent = agent.copy()
        updated_agent["opinion"] = response.get("new_opinion", agent["opinion"])
        updated_agent["score"] = new_score
        updated_agent["stance"] = response.get("new_stance", agent["stance"])
        updated_agent["opinion_delta"] = opinion_delta
        updated_agent["last_argument"] = response.get("argument", "")
        updated_agent["shifted"] = response.get("shifted", False)
        updated_agent["shift_reason"] = response.get("shift_reason", "")
        updated_agent["key_evidence_used"] = response.get("key_evidence_used", [])

        return updated_agent

    except Exception as e:
        print(f"[DebateEngine] Error in round {round_num} for agent {agent['name']}: {e}")
        return agent

async def run_debate_round(
    agents: list[dict],
    topic: str,
    G: nx.DiGraph,
    round_num: int
) -> list[dict]:
    """
    Run all agents through a debate round in parallel.
    Every agent thinks simultaneously — no sequential bottleneck.
    """
    print(f"[DebateEngine] Running round {round_num} with {len(agents)} agents...")

    tasks = [
        run_single_agent_round(
            agent=agent,
            all_agents=agents,
            topic=topic,
            G=G,
            round_num=round_num
        )
        for agent in agents
    ]

    updated_agents = await asyncio.gather(*tasks)
    return list(updated_agents)

async def run_debate(
    topic: str,
    agents: list[dict],
    G: nx.DiGraph,
    num_rounds: int = 3
) -> dict:
    """
    Run the full structured debate.
    Returns all rounds with agent states and opinion trajectories.
    """
    print(f"[DebateEngine] Starting debate on: {topic}")
    print(f"[DebateEngine] {len(agents)} agents, {num_rounds} rounds")

    all_rounds = []
    current_agents = agents.copy()

    for round_num in range(1, num_rounds + 1):
        updated_agents = await run_debate_round(
            agents=current_agents,
            topic=topic,
            G=G,
            round_num=round_num
        )

        # Record this round
        round_result = {
            "round": round_num,
            "agents": [
                {
                    "id": a["id"],
                    "name": a["name"],
                    "persona": a["persona"],
                    "opinion": a["opinion"],
                    "score": a["score"],
                    "opinion_delta": a["opinion_delta"],
                    "stance": a["stance"],
                }
                for a in updated_agents
            ]
        }

        all_rounds.append(round_result)
        current_agents = updated_agents

        print(f"[DebateEngine] Round {round_num} complete. "
              f"Shifts: {sum(1 for a in updated_agents if a.get('shifted', False))}/{len(updated_agents)}")

    return {
        "rounds": all_rounds,
        "final_agents": current_agents
    }