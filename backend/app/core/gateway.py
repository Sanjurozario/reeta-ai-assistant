import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
import httpx

from app.config import settings

logger = logging.getLogger("reeta.gateway")


class GatewayMessage(BaseModel):
    role: str  # 'system', 'user', 'assistant'
    content: str


class GatewayResponse(BaseModel):
    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    raw: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """Abstract Base Class for all AI model providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if minimum required credentials/endpoints are set."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Pings provider API or health check endpoint."""
        pass

    @abstractmethod
    async def generate(
        self,
        messages: List[GatewayMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout_seconds: float = 30.0,
    ) -> GatewayResponse:
        pass


# ============================================================================
# 1. OpenAI-Compatible Provider
# ============================================================================

class OpenAIProvider(BaseLLMProvider):
    """OpenAI and OpenAI-compatible API provider (OpenAI, Groq, DeepSeek, vLLM)."""

    def __init__(self):
        self._client = None
        # Load from Windows Credential Manager if settings is empty
        if not settings.OPENAI_API_KEY:
            try:
                import keyring
                stored = keyring.get_password("REETA", "OPENAI_API_KEY")
                if stored:
                    settings.OPENAI_API_KEY = stored
                    stored_m = keyring.get_password("REETA", "OPENAI_DEFAULT_MODEL")
                    if stored_m:
                        settings.OPENAI_DEFAULT_MODEL = stored_m
            except Exception:
                pass

        if self.is_configured():
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                )
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")

    def update_key(self, api_key: str, model: Optional[str] = None, base_url: Optional[str] = None):
        settings.OPENAI_API_KEY = api_key
        if model:
            settings.OPENAI_DEFAULT_MODEL = model
        if base_url:
            settings.OPENAI_BASE_URL = base_url
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.OPENAI_BASE_URL,
        )

    def remove_key(self):
        settings.OPENAI_API_KEY = ""
        self._client = None

    async def test_connection(self) -> Dict[str, Any]:
        if not self._client or not self.is_configured():
            return {"success": False, "error": "OpenAI API key not configured.", "provider": "openai"}
        t0 = time.perf_counter()
        try:
            models = await asyncio.wait_for(self._client.models.list(), timeout=10.0)
            ms = int((time.perf_counter() - t0) * 1000)
            return {
                "success": True,
                "provider": "openai",
                "model": settings.OPENAI_DEFAULT_MODEL,
                "latency_ms": ms,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "openai"}

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_configured(self) -> bool:
        return bool(settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 0)

    async def is_available(self) -> bool:
        if not self.is_configured() or not self._client:
            return False
        try:
            await asyncio.wait_for(self._client.models.list(), timeout=5.0)
            return True
        except Exception as e:
            logger.debug(f"OpenAI ping failed: {e}")
            return False

    async def generate(
        self,
        messages: List[GatewayMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout_seconds: float = 30.0,
    ) -> GatewayResponse:
        if not self._client:
            raise RuntimeError("OpenAI provider is not configured with an API key.")

        target_model = model or settings.OPENAI_DEFAULT_MODEL
        payload_messages = [{"role": m.role, "content": m.content} for m in messages]

        t0 = time.perf_counter()
        response = await asyncio.wait_for(
            self._client.chat.completions.create(
                model=target_model,
                messages=payload_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            timeout=timeout_seconds,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        choice = response.choices[0]
        usage = response.usage

        return GatewayResponse(
            content=choice.message.content or "",
            provider=self.provider_name,
            model=target_model,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
        )


# ============================================================================
# 2. Anthropic Claude Provider
# ============================================================================

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude API Provider."""

    def __init__(self):
        self._client = None
        if self.is_configured():
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic client: {e}")

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def is_configured(self) -> bool:
        return bool(settings.ANTHROPIC_API_KEY and len(settings.ANTHROPIC_API_KEY.strip()) > 0)

    async def is_available(self) -> bool:
        return self.is_configured()

    async def generate(
        self,
        messages: List[GatewayMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout_seconds: float = 30.0,
    ) -> GatewayResponse:
        if not self._client:
            raise RuntimeError("Anthropic provider is not configured with an API key.")

        target_model = model or settings.ANTHROPIC_DEFAULT_MODEL
        system_prompt = ""
        user_assistant_messages = []

        for m in messages:
            if m.role == "system":
                system_prompt += m.content + "\n"
            else:
                user_assistant_messages.append({"role": m.role, "content": m.content})

        t0 = time.perf_counter()
        response = await asyncio.wait_for(
            self._client.messages.create(
                model=target_model,
                max_tokens=max_tokens or 4096,
                temperature=temperature,
                system=system_prompt.strip() or None,
                messages=user_assistant_messages,
            ),
            timeout=timeout_seconds,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        content = ""
        for block in response.content:
            if hasattr(block, "text"):
                content += block.text

        return GatewayResponse(
            content=content,
            provider=self.provider_name,
            model=target_model,
            prompt_tokens=response.usage.input_tokens if response.usage else 0,
            completion_tokens=response.usage.output_tokens if response.usage else 0,
            latency_ms=latency_ms,
        )


# ============================================================================
# 3. Google Gemini Provider
# ============================================================================

class GeminiProvider(BaseLLMProvider):
    """Google Gemini API Provider."""

    def __init__(self):
        self._client = None
        if self.is_configured():
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI client: {e}")

    @property
    def provider_name(self) -> str:
        return "gemini"

    def is_configured(self) -> bool:
        return bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 0)

    async def is_available(self) -> bool:
        return self.is_configured()

    async def generate(
        self,
        messages: List[GatewayMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout_seconds: float = 30.0,
    ) -> GatewayResponse:
        if not self._client:
            raise RuntimeError("Gemini provider is not configured with an API key.")

        target_model = model or settings.GEMINI_DEFAULT_MODEL
        # Concatenate conversation
        prompt_parts = []
        for m in messages:
            prompt_parts.append(f"{m.role.upper()}: {m.content}")
        full_prompt = "\n\n".join(prompt_parts)

        t0 = time.perf_counter()
        loop = asyncio.get_running_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model=target_model,
                    contents=full_prompt,
                ),
            ),
            timeout=timeout_seconds,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        return GatewayResponse(
            content=response.text or "",
            provider=self.provider_name,
            model=target_model,
            prompt_tokens=0,
            completion_tokens=0,
            latency_ms=latency_ms,
        )


# ============================================================================
# 4. Ollama Provider (Optional Local Provider)
# ============================================================================

class OllamaProvider(BaseLLMProvider):
    """Ollama local model server provider."""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama"

    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        messages: List[GatewayMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout_seconds: float = 45.0,
    ) -> GatewayResponse:
        target_model = model or settings.OLLAMA_DEFAULT_MODEL
        payload_messages = [{"role": m.role, "content": m.content} for m in messages]

        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            res = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": target_model,
                    "messages": payload_messages,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
            )
            res.raise_for_status()
            data = res.json()

        latency_ms = int((time.perf_counter() - t0) * 1000)
        content = data.get("message", {}).get("content", "")

        return GatewayResponse(
            content=content,
            provider=self.provider_name,
            model=target_model,
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            latency_ms=latency_ms,
        )


# ============================================================================
# 5. Fallback Mock Provider (For zero-credential local test environments)
# ============================================================================

class MockTestingProvider(BaseLLMProvider):
    """Deterministic simulation provider ensuring tests pass without network or keys."""

    @property
    def provider_name(self) -> str:
        return "mock"

    def is_configured(self) -> bool:
        return True

    async def is_available(self) -> bool:
        return True

    async def generate(
        self,
        messages: List[GatewayMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout_seconds: float = 5.0,
    ) -> GatewayResponse:
        last_msg = messages[-1].content if messages else "Hello"
        lower_msg = last_msg.lower()

        if "research" in lower_msg or "search" in lower_msg or "news" in lower_msg or "citations" in lower_msg:
            content = (
                "[REETA Mock Mode - Simulated Intelligence]\n"
                "Executive Summary: Latest advancements in personal AI highlight breakthroughs in multi-agent orchestration, "
                "local OS automation, and zero-trust permission boundaries.\n\n"
                "Key Findings:\n"
                "1. Autonomous execution engines utilize LangGraph state machines for deterministic task completion.\n"
                "2. Zero-trust policy gates require human approval for consequential operating system actions.\n"
                "3. Cognitive semantic memories backed by PostgreSQL pgvector enable persistent recall across independent sessions.\n\n"
                "Verified Sources & Citations:\n"
                "- https://news.ycombinator.com (Autonomous Systems Report 2026)\n"
                "- https://en.wikipedia.org/wiki/Artificial_intelligence (State of Agent Architectures)\n"
                "- https://python.org (Python 3.11 Runtime Benchmarks)"
            )
        elif "prefer" in lower_msg or "dark mode" in lower_msg:
            content = "[REETA Mock Mode - Simulated Intelligence] User preference identified: Dark mode theme with high-contrast holographic cyan styling."
        else:
            content = f"[REETA Mock Mode - Simulated Intelligence] Successfully executed objective: '{last_msg[:60]}'."

        return GatewayResponse(
            content=content,
            provider="mock",
            model="reeta-mock-v1",
            prompt_tokens=15,
            completion_tokens=45,
            latency_ms=10,
        )


# ============================================================================
# 6. Central Model Gateway
# ============================================================================

class ModelGateway:
    """Central provider-independent orchestrator for LLM routing and execution."""

    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "gemini": GeminiProvider(),
            "ollama": OllamaProvider(),
            "mock": MockTestingProvider(),
        }

    def get_provider(self, name: str) -> Optional[BaseLLMProvider]:
        return self._providers.get(name.lower().strip())

    async def get_active_providers_status(self) -> Dict[str, Any]:
        """Returns diagnostic status of all registered providers."""
        status = {}
        for name, provider in self._providers.items():
            is_cfg = provider.is_configured()
            is_avail = False
            if is_cfg and name != "mock":
                try:
                    is_avail = await provider.is_available()
                except Exception:
                    is_avail = False
            elif name == "mock":
                is_avail = True

            status[name] = {
                "configured": is_cfg,
                "available": is_avail,
            }
        return status

    async def get_active_provider_name(self) -> str:
        """Determines the current functional active provider name."""
        status = await self.get_active_providers_status()
        pref = settings.DEFAULT_MODEL_PROVIDER.lower().strip()
        if status.get(pref, {}).get("available"):
            return pref
        for p in ["openai", "anthropic", "gemini", "ollama", "mock"]:
            if status.get(p, {}).get("available"):
                return p
        return "mock"

    def update_openai_credentials(self, api_key: str, model: Optional[str] = None):
        import keyring
        try:
            keyring.set_password("REETA", "OPENAI_API_KEY", api_key)
            if model:
                keyring.set_password("REETA", "OPENAI_DEFAULT_MODEL", model)
        except Exception as e:
            logger.warning(f"Could not persist to Windows Credential Manager: {e}")

        prov = self._providers.get("openai")
        if isinstance(prov, OpenAIProvider):
            prov.update_key(api_key, model=model)
        settings.DEFAULT_MODEL_PROVIDER = "openai"

    def remove_openai_credentials(self):
        import keyring
        try:
            keyring.delete_password("REETA", "OPENAI_API_KEY")
        except Exception:
            pass
        try:
            keyring.delete_password("REETA", "OPENAI_DEFAULT_MODEL")
        except Exception:
            pass
        prov = self._providers.get("openai")
        if isinstance(prov, OpenAIProvider):
            prov.remove_key()
        settings.DEFAULT_MODEL_PROVIDER = "mock"

    async def get_credential_status(self) -> Dict[str, Any]:
        prov = self._providers.get("openai")
        has_key = bool(settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 5)
        active_name = await self.get_active_provider_name()

        if has_key:
            if isinstance(prov, OpenAIProvider) and await prov.is_available():
                status = "live"
                detail = f"Connected to OpenAI ({settings.OPENAI_DEFAULT_MODEL})"
            else:
                status = "error"
                detail = "OpenAI API key configured, but ping failed. Check network or key validity."
        else:
            status = "mock"
            detail = "Mock Provider active (Simulated intelligence for testing). Enter an OpenAI API key for live execution."

        return {
            "configured": has_key,
            "provider": active_name,
            "model": settings.OPENAI_DEFAULT_MODEL,
            "status": status,
            "status_detail": detail,
            "available_models": ["gpt-4o", "gpt-4o-mini", "o1-mini", "o3-mini", "gpt-3.5-turbo"],
        }

    async def generate_with_fallback(
        self,
        messages: List[GatewayMessage],
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        fallback_order: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        task_id: Optional[str] = None,
    ) -> GatewayResponse:
        """
        Attempts execution using preferred provider.
        If unconfigured or fails, cascades through fallbacks.
        Falls back to 'mock' if no external provider is available.
        """
        primary = preferred_provider or settings.DEFAULT_MODEL_PROVIDER
        candidates = [primary] + (fallback_order or ["openai", "anthropic", "gemini", "ollama", "mock"])

        # Deduplicate while preserving order
        ordered = []
        for c in candidates:
            c_norm = c.lower().strip()
            if c_norm in self._providers and c_norm not in ordered:
                ordered.append(c_norm)

        last_error = None
        for candidate_name in ordered:
            prov = self._providers[candidate_name]
            if not prov.is_configured() and candidate_name != "mock":
                continue

            try:
                target_m = preferred_model if candidate_name == primary else None
                logger.info(
                    f"[Task {task_id or 'global'}] [LLM Gateway] Dispatching to '{candidate_name}' "
                    f"(model={target_m or 'default'})"
                )
                t_start = time.perf_counter()
                response = await prov.generate(
                    messages=messages,
                    model=target_m,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                elapsed_ms = int((time.perf_counter() - t_start) * 1000)
                logger.info(
                    f"[Task {task_id or 'global'}] [LLM Gateway] Provider '{candidate_name}' succeeded in "
                    f"{elapsed_ms}ms (tokens: prompt={response.prompt_tokens}, completion={response.completion_tokens})"
                )
                return response
            except Exception as e:
                logger.warning(
                    f"[Task {task_id or 'global'}] [LLM Gateway] Provider '{candidate_name}' generation failed: "
                    f"{type(e).__name__}: {e}. Cascading to fallback."
                )
                last_error = e

        raise RuntimeError(f"All model providers failed or are unconfigured. Last error: {last_error}")


# Global Gateway Singleton
model_gateway = ModelGateway()
