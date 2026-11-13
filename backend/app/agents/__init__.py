from app.agents.base import BaseAgent, AgentStepResult
from app.agents.workers import (
    AssistantAgent,
    ResearchAgent,
    CodingAgent,
    ComputerAgent,
    BrowserAgent,
    FileAgent,
    ProductivityAgent,
    MemoryAgent,
)

# Active Specialized Worker Registry
_agents = {
    "assistant": AssistantAgent(),
    "conversational": AssistantAgent(),
    "research": ResearchAgent(),
    "coding": CodingAgent(),
    "computer": ComputerAgent(),
    "browser": BrowserAgent(),
    "file": FileAgent(),
    "productivity": ProductivityAgent(),
    "memory": MemoryAgent(),
}


def get_agent(agent_type: str) -> BaseAgent:
    """Returns specialized worker agent or defaults to assistant agent."""
    norm = agent_type.lower().replace("_agent", "").strip()
    return _agents.get(norm, _agents["assistant"])


__all__ = [
    "BaseAgent",
    "AgentStepResult",
    "AssistantAgent",
    "ResearchAgent",
    "CodingAgent",
    "ComputerAgent",
    "BrowserAgent",
    "FileAgent",
    "ProductivityAgent",
    "MemoryAgent",
    "get_agent",
]

