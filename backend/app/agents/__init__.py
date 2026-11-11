from app.agents.base import BaseAgent, AgentStepResult
from app.agents.workers import (
    ResearchAgent,
    CodingAgent,
    ComputerAgent,
    BrowserAgent,
    FileAgent,
    ProductivityAgent,
)

# Active Specialized Worker Registry
_agents = {
    "research": ResearchAgent(),
    "coding": CodingAgent(),
    "computer": ComputerAgent(),
    "browser": BrowserAgent(),
    "file": FileAgent(),
    "productivity": ProductivityAgent(),
}


def get_agent(agent_type: str) -> BaseAgent:
    """Returns specialized worker agent or defaults to research agent."""
    norm = agent_type.lower().replace("_agent", "").strip()
    return _agents.get(norm, _agents["research"])


__all__ = [
    "BaseAgent",
    "AgentStepResult",
    "ResearchAgent",
    "CodingAgent",
    "ComputerAgent",
    "BrowserAgent",
    "FileAgent",
    "ProductivityAgent",
    "get_agent",
]
