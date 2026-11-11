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
        if self.is_configured():
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    base_url=settings.OPENAI_BASE_URL,
                )
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")

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
        return GatewayResponse(
            content=f"[REETA Mock Agent Response] Processed objective: '{last_msg}' successfully.",
            provider="mock",
            model="reeta-mock-v1",
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=12,
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

    async def generate_with_fallback(
        self,
        messages: List[GatewayMessage],
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        fallback_order: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
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
                logger.info(f"Dispatching query to model provider '{candidate_name}'")
                response = await prov.generate(
                    messages=messages,
                    model=preferred_model if candidate_name == primary else None,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return response
            except Exception as e:
                logger.warning(f"Provider '{candidate_name}' generation failed: {e}. Cascading to fallback.")
                last_error = e

        raise RuntimeError(f"All model providers failed or are unconfigured. Last error: {last_error}")


# Global Gateway Singleton
model_gateway = ModelGateway()
