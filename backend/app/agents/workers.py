import logging
from typing import List
from app.agents.base import BaseAgent

logger = logging.getLogger("reeta.agents.workers")


class ResearchAgent(BaseAgent):
    name = "research_agent"
    role_description = "Conducts deep web research, verifies facts, and compiles structured PDF/Markdown reports."
    system_prompt = (
        "You are the REETA Research Agent. Your responsibility is to query online sources, "
        "cross-reference facts, and compile clear, verifiable reports with citations."
    )
    assigned_tools = ["web_search", "create_pdf_report"]


class CodingAgent(BaseAgent):
    name = "coding_agent"
    role_description = "Navigates codebases, analyzes syntax, applies patches, and executes automated test suites."
    system_prompt = (
        "You are the REETA Coding Agent. You inspect codebases, identify bugs, construct minimal "
        "and clean patches, and run test suites to empirically verify correctness."
    )
    assigned_tools = ["code_search", "code_patch", "run_tests", "run_script", "read_file", "write_file"]


class ComputerAgent(BaseAgent):
    name = "computer_agent"
    role_description = "Interacts with Windows 11 desktop applications, active windows, mouse, keyboard, and screen capture."
    system_prompt = (
        "You are the REETA Computer Agent. You operate the Windows 11 host using UI Automation, "
        "verify running application processes, and capture screen states."
    )
    assigned_tools = ["list_open_windows", "open_application", "capture_screen", "type_text"]


class BrowserAgent(BaseAgent):
    name = "browser_agent"
    role_description = "Operates Chromium browser sessions via Playwright, extracts structured data, and fills forms."
    system_prompt = (
        "You are the REETA Browser Agent. You automate web tasks using Playwright, safely treat "
        "webpage data as untrusted, and extract required tables and elements."
    )
    assigned_tools = ["browser_navigate", "browser_extract_tables"]


class FileAgent(BaseAgent):
    name = "file_agent"
    role_description = "Manages files, batch organizes directories, reads/writes documents, and generates PDF exports."
    system_prompt = (
        "You are the REETA File Agent. You search, read, write, and organize files within authorized "
        "workspaces, enforcing exact byte verification on disk."
    )
    assigned_tools = [
        "file_search",
        "read_file",
        "write_file",
        "organize_folder",
        "create_directory",
        "delete_file",
        "create_pdf_report",
    ]


class ProductivityAgent(BaseAgent):
    name = "productivity_agent"
    role_description = "Schedules tasks, sets reminders, and triggers automated alerts."
    system_prompt = (
        "You are the REETA Productivity Agent. You manage user reminders, calendar agendas, "
        "and task schedules."
    )
    assigned_tools = ["create_reminder"]


class MemoryAgent(BaseAgent):
    name = "memory_agent"
    role_description = "Manages long-term semantic facts, user preferences, and episodic memory recall via pgvector."
    system_prompt = (
        "You are the REETA Memory Agent. You store user preferences, recall relevant context, "
        "and delete forgotten memories using pgvector cosine similarity search."
    )
    assigned_tools = []

    async def run_step(
        self,
        step_title: str,
        task_objective: str,
        context: dict,
        session,
        task_id=None,
        task_step_id=None,
        user_id=None,
        approval_token=None,
    ):
        import re
        import uuid
        from app.memory.store import MemoryService
        from app.agents.base import AgentStepResult

        effective_user_id = user_id or uuid.UUID("00000000-0000-0000-0000-000000000001")
        title_lower = step_title.lower()
        obj_lower = task_objective.lower()

        # 1. Recall / Search Memory
        if "retrieve" in title_lower or "search" in title_lower or "recall" in title_lower or "what" in obj_lower:
            query = re.sub(r'^(hey reeta,?\s*|what do i prefer\??|what is my\s*)', '', task_objective, flags=re.I).strip() or "preference"
            memories = await MemoryService.search_memories(
                session=session,
                user_id=effective_user_id,
                query=query,
                top_k=3,
            )
            if not memories:
                # Fallback to listing all memories for user
                all_m = await MemoryService.list_memories(session=session, user_id=effective_user_id, limit=5)
                memories = all_m

            if memories:
                top_match = memories[0]
                content = top_match.get("content", "")
                sim = top_match.get("similarity_score", 1.0)
                synthesized = f"Based on your stored preferences in cognitive memory, you prefer {content}."
                return AgentStepResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="recall_memory",
                    output={"answer": synthesized, "matched_memory": content, "similarity": sim},
                    verified=True,
                    verification_evidence=f"Recalled preference from pgvector memory (similarity: {sim}): '{content}'.",
                )
            else:
                return AgentStepResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="recall_memory",
                    output={"answer": "No specific preference has been stored yet.", "matched_memory": None},
                    verified=True,
                    verification_evidence="Cognitive memory query executed cleanly against pgvector database.",
                )

        # 2. Store / Persist Memory
        content = re.sub(r'^(hey reeta,?\s*|remember that\s*|remember\s*|please remember\s*)', '', task_objective, flags=re.I).strip()
        if not content:
            content = task_objective

        memory_rec = await MemoryService.store_memory(
            session=session,
            user_id=effective_user_id,
            content=content,
            memory_type="preference",
            category="user_preference",
        )
        return AgentStepResult(
            success=True,
            agent_name=self.name,
            action_taken="store_memory",
            output={"memory_id": str(memory_rec.id), "content": memory_rec.content, "type": "preference"},
            verified=True,
            verification_evidence=f"Empirically persisted preference to PostgreSQL pgvector memory: '{content}'.",
        )


