from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.voice.service import VoiceService

router = APIRouter(prefix="/voice", tags=["Voice Engine"])


class TranscribeRequest(BaseModel):
    audio_base64: Optional[str] = Field(None, description="Base64-encoded audio payload")
    text_mock: Optional[str] = Field(None, description="Optional text simulation for testing")


class SynthesizeRequest(BaseModel):
    text: str = Field(..., description="Text content to speak")
    voice: Optional[str] = Field("en_US-lessac-medium", description="TTS voice identifier")


class ModeRequest(BaseModel):
    mode: str = Field(..., description="'voice' or 'text'")


@router.get("/status")
async def get_voice_status():
    return {
        "status": "ready",
        "conversation_mode": VoiceService.get_conversation_mode(),
        "wake_word_supported": True,
        "interrupted": VoiceService._interrupted,
    }


@router.post("/transcribe")
async def transcribe_audio(req: TranscribeRequest):
    result = await VoiceService.transcribe_audio(
        audio_bytes=req.audio_base64.encode() if req.audio_base64 else None,
        text_fallback=req.text_mock,
    )
    return result


@router.post("/synthesize")
async def synthesize_speech(req: SynthesizeRequest):
    result = await VoiceService.synthesize_speech(text=req.text, voice=req.voice)
    return result


@router.post("/interrupt")
async def interrupt_speech():
    return VoiceService.interrupt_speech()


@router.post("/mode")
async def set_conversation_mode(req: ModeRequest):
    if req.mode not in ("text", "voice"):
        raise HTTPException(status_code=400, detail="Mode must be 'text' or 'voice'")
    new_mode = VoiceService.set_conversation_mode(req.mode)
    return {"status": "ok", "conversation_mode": new_mode}
