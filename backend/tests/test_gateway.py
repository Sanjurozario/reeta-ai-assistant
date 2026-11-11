import pytest
from app.core.gateway import model_gateway, GatewayMessage


@pytest.mark.asyncio
async def test_gateway_providers_registration():
    status = await model_gateway.get_active_providers_status()
    assert "openai" in status
    assert "anthropic" in status
    assert "gemini" in status
    assert "ollama" in status
    assert "mock" in status
    assert status["mock"]["available"] is True


@pytest.mark.asyncio
async def test_gateway_fallback_generation():
    # Prompt the gateway; with unconfigured cloud keys, it gracefully falls back to mock provider
    messages = [
        GatewayMessage(role="system", content="You are a helpful assistant."),
        GatewayMessage(role="user", content="What is 2+2?"),
    ]
    response = await model_gateway.generate_with_fallback(
        messages=messages,
        preferred_provider="openai",
    )
    assert response is not None
    assert len(response.content) > 0
    assert response.provider in {"openai", "anthropic", "gemini", "ollama", "mock"}
    assert response.latency_ms >= 0
