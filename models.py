from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

# ─── Enums ───────────────────────────────────────────

class Stance(str, Enum):
    for_ = "for"
    against = "against"
    neutral = "neutral"

class SimulationStatus(str, Enum):
    running = "running"
    completed = "completed"
    failed = "failed"

# ─── Agent Models ────────────────────────────────────

class AgentState(BaseModel):
    id: str
    name: str
    persona: str
    opinion: str
    score: float
    opinion_delta: float
    stance: Stance

class RoundResult(BaseModel):
    round: int
    agents: List[AgentState]

class AgentMemory(BaseModel):
    simulation_id: str
    date: str
    topic: str
    final_opinion: str
    final_score: float
    shifted: bool

class AgentProfile(BaseModel):
    agent_id: str
    name: str
    persona: str
    memory: List[AgentMemory]

# ─── Simulation Models ───────────────────────────────

class SimulationStartRequest(BaseModel):
    topic: str
    num_agents: int = 20
    num_rounds: int = 3
    uploads: Optional[List[str]] = []

class SimulationStartResponse(BaseModel):
    simulation_id: str
    status: SimulationStatus
    agents_created: int

class SimulationDebateResponse(BaseModel):
    simulation_id: str
    rounds: List[RoundResult]

# ─── Injection Models ────────────────────────────────

class InjectionRequest(BaseModel):
    simulation_id: str
    event: str

class AgentReaction(BaseModel):
    agent_id: str
    name: str
    opinion_before: str
    opinion_after: str
    delta: float
    shifted: bool

class InjectionResponse(BaseModel):
    injected_at_tick: int
    reactions: List[AgentReaction]

# ─── Branch Models ───────────────────────────────────

class BranchRequest(BaseModel):
    simulation_id: str
    from_tick: int

class BranchResponse(BaseModel):
    branch_id: str
    parent_simulation_id: str
    branched_at_tick: int
    status: SimulationStatus

# ─── Report Models ───────────────────────────────────

class DecisiveArgument(BaseModel):
    agent_id: str
    argument: str
    influenced_agents: List[str]

class AgentSummary(BaseModel):
    agent_id: str
    name: str
    shifted: bool
    final_stance: Stance
    key_moment: str

class ReportResponse(BaseModel):
    simulation_id: str
    topic: str
    summary: str
    agents_shifted: int
    agents_held: int
    decisive_arguments: List[DecisiveArgument]
    predicted_trajectory: str
    agent_summaries: List[AgentSummary]

# ─── Sentiment Models ────────────────────────────────

class SentimentTick(BaseModel):
    tick: int
    positive: float
    neutral: float
    negative: float

class SentimentHistoryResponse(BaseModel):
    simulation_id: str
    ticks: List[SentimentTick]