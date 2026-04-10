import json
import asyncio
import uuid
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from backend.utils.llm_client import call_llm_json
from backend.utils.graph_utils import get_most_influential, get_nodes_by_type
import networkx as nx

# Force stance diversity across agents
STANCE_MAP = {0: "strongly against", 1: "strongly for", 2: "neutral"}
SCORE_RANGE = {
    "strongly against": (1.5, 3.5),
    "strongly for": (7.5, 9.5),
    "neutral": (4.0, 6.0)
}

async def generate_single_persona(
    topic: str,
    G: nx.DiGraph,
    agent_index: int,
    existing_names: list[str]
) -> dict:
    """Generate a single grounded agent persona from the knowledge graph."""

    # Pull the most influential nodes from the graph
    influential_nodes = get_most_influential(G, top_n=15)
    claims = get_nodes_by_type(G, "claim")

    # Format graph context for the LLM
    graph_context = "\n".join([
        f"- {n['name']} (cited {n['citations']}x, influence: {n['influence_score']:.3f}): {n.get('description', '')[:100]}"
        for n in influential_nodes
    ])

    claims_context = "\n".join([
        f"- {c['name'][:100]} [{c.get('sentiment', 'neutral')}]"
        for c in claims[:10]
    ])

    # Force a specific stance based on agent index
    forced_stance = STANCE_MAP[agent_index % 3]
    score_min, score_max = SCORE_RANGE[forced_stance]
    existing_names_str = ", ".join(existing_names) if existing_names else "none"

    system = """You are designing a realistic human persona for a debate simulation.
The persona must be grounded in the provided real-world knowledge graph data.
Always respond in valid JSON."""

    prompt = f"""Create a unique and realistic debate persona for agent {agent_index + 1}.

Topic being debated: {topic}

Real-world knowledge graph context:
Key entities and concepts:
{graph_context}

Key claims found in sources:
{claims_context}

Names already used by other agents: {existing_names_str}
(You MUST use a completely different name)

Generate a persona that:
1. Has a specific demographic background (age, profession, location)
2. Has an opinion grounded in specific entities/claims from the knowledge graph above
3. Feels like a real person, not a caricature

Respond in this exact JSON format:
{{
    "name": "full name",
    "age": 30,
    "profession": "job title",
    "location": "city, country",
    "persona": "2-3 sentence personality and background description",
    "initial_opinion": "their specific opinion on the topic in 2 sentences, citing specific facts from the knowledge graph",
    "key_beliefs": ["belief 1 grounded in graph", "belief 2 grounded in graph"],
    "persuasion_resistance": 0.5,
    "known_entities": ["entity1", "entity2", "entity3"]
}}

Rules:
- initial_stance is LOCKED to: {forced_stance}
- initial_score must be between {score_min} and {score_max} to reflect that stance
- persuasion_resistance is between 0.1 (easily convinced) and 0.9 (very hard to convince)
- known_entities must be actual entity names from the knowledge graph context above
- initial_opinion must reference specific facts, not generic statements
- Name must be unique — do NOT use any of these names: {existing_names_str}
- Generate diverse demographics — vary nationality, age, profession"""

    try:
        result = await call_llm_json(prompt, system)
        persona = json.loads(result)

        import random
        score = round(random.uniform(score_min, score_max), 1)

        return {
            "id": f"agent_{uuid.uuid4().hex[:8]}",
            "name": persona.get("name", f"Agent {agent_index + 1}"),
            "age": persona.get("age", 30),
            "profession": persona.get("profession", ""),
            "location": persona.get("location", ""),
            "persona": persona.get("persona", ""),
            "stance": forced_stance.replace("strongly ", "").replace("strongly against", "against").replace("strongly for", "for"),
            "opinion": persona.get("initial_opinion", ""),
            "score": score,
            "opinion_delta": 0.0,
            "key_beliefs": persona.get("key_beliefs", []),
            "persuasion_resistance": float(persona.get("persuasion_resistance", 0.5)),
            "known_entities": persona.get("known_entities", []),
            "memory": []
        }
    except Exception as e:
        import traceback
        print(f"[PersonaGenerator] Error generating persona {agent_index}: {e}")
        traceback.print_exc()
        return None

async def generate_personas(
    topic: str,
    G: nx.DiGraph,
    num_agents: int = 20
) -> list[dict]:
    print(f"[PersonaGenerator] Generating {num_agents} personas for topic: {topic}")

    existing_names = []
    valid_personas = []

    # Run sequentially to guarantee unique names and correct stance cycling
    for i in range(num_agents):
        await asyncio.sleep(0.5)  # small delay between calls
        persona = await generate_single_persona(topic, G, i, existing_names.copy())
        if persona:
            existing_names.append(persona["name"])
            valid_personas.append(persona)
            print(f"[PersonaGenerator] Agent {i+1}: {persona['name']} | stance: {persona['stance']} | score: {persona['score']}")

    print(f"[PersonaGenerator] Successfully generated {len(valid_personas)} personas")
    return valid_personas