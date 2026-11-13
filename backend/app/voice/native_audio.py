import asyncio
import io
import logging
import os
import queue
import re
import subprocess
import threading
import time
from typing import Optional, List, Dict, Any
import numpy as np

from app.config import settings
from app.core.tasks import broadcaster
from app.voice.service import VoiceService

logger = logging.getLogger("reeta.voice.native")


class NativeAudioPipeline:
    """
    Native Windows microphone listener, VAD, wake-word detector,
    and hybrid neural/SAPI offline speech synthesis pipeline.
    """

    def __init__(self):
        self._running = False
        self._muted = False
        self._stream = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._audio_queue: queue.Queue = queue.Queue(maxsize=100)
        self._process_thread: Optional[threading.Thread] = None
        self._last_level_emit_time = 0.0
        self._sample_rate = 16000
        self._vad_threshold = 0.02
        self._silence_duration_trigger = 0.65
        self._whisper_model = None
        self._tts_lock = threading.Lock()
        self._tts_engine = None
        self._current_speaking = False
        self._mic_error: Optional[str] = None

    def init_whisper(self):
        """Lazy loader for faster-whisper model."""
        if self._whisper_model is None:
            try:
                from faster_whisper import WhisperModel
                logger.info("Initializing faster-whisper tiny.en model on CPU int8...")
                self._whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
                logger.info("faster-whisper model loaded.")
            except Exception as e:
                logger.warning(f"Could not initialize faster-whisper: {e}")
        return self._whisper_model

    def start(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Starts background audio capture and event loop dispatch."""
        if self._running:
            return
        self._loop = loop or asyncio.get_event_loop()
        self._running = True
        self._mic_error = None

        try:
            import sounddevice as sd
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocksize=1024,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._process_thread = threading.Thread(target=self._vad_worker, daemon=True)
            self._process_thread.start()
            logger.info("Native audio capture pipeline started.")
        except Exception as e:
            self._mic_error = str(e)
            logger.warning(f"Failed to start sounddevice microphone capture: {e}")
            if self._loop and not self._loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    broadcaster.broadcast(
                        event="mic_denied",
                        payload={
                            "denied": True,
                            "error": str(e),
                            "message": "Microphone access is denied or audio device unavailable in Windows settings.",
                            "settings_uri": "ms-settings:privacy-microphone",
                        },
                    ),
                    self._loop,
                )

    def stop(self):
        """Stops audio capture."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        logger.info("Native audio capture pipeline stopped.")

    def mute(self):
        self._muted = True

    def unmute(self):
        self._muted = False

    def is_muted(self) -> bool:
        return self._muted

    @staticmethod
    def open_microphone_settings():
        """Opens Windows 11 Microphone privacy settings."""
        try:
            subprocess.Popen("start ms-settings:privacy-microphone", shell=True)
            return True
        except Exception:
            return False

    def _audio_callback(self, indata, frames, time_info, status):
        """Invoked by sounddevice in high-priority audio thread."""
        if not self._running or self._muted:
            return

        data = indata.flatten()
        rms = float(np.sqrt(np.mean(data**2)))

        now = time.time()
        if now - self._last_level_emit_time >= 0.05:  # 20 Hz visual update
            self._last_level_emit_time = now
            visual_level = min(1.0, rms * 15.0)
            if self._loop and not self._loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    broadcaster.broadcast(
                        event="audio_level",
                        payload={"level": round(visual_level, 3), "rms": round(rms, 4)},
                    ),
                    self._loop,
                )

        # Barge-in: user speaking while TTS is active
        if rms > (self._vad_threshold * 1.5) and self._current_speaking:
            logger.info("Barge-in detected: User speaking while REETA is outputting voice.")
            self.stop_speaking()

        try:
            self._audio_queue.put_nowait((data.copy(), rms))
        except queue.Full:
            pass

    def _vad_worker(self):
        """Background thread accumulating speech frames and triggering transcription."""
        speech_buffer: List[np.ndarray] = []
        is_speech_active = False
        last_speech_time = 0.0

        while self._running:
            try:
                data, rms = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            now = time.time()
            if rms > self._vad_threshold:
                if not is_speech_active:
                    is_speech_active = True
                    logger.debug("VAD: Speech onset detected.")
                    if self._loop and not self._loop.is_closed():
                        asyncio.run_coroutine_threadsafe(
                            broadcaster.broadcast(event="listening_state", payload={"is_listening": True}),
                            self._loop,
                        )
                last_speech_time = now
                speech_buffer.append(data)
            elif is_speech_active:
                speech_buffer.append(data)
                # Check silence pause duration
                if (now - last_speech_time) > self._silence_duration_trigger:
                    is_speech_active = False
                    total_samples = sum(len(c) for c in speech_buffer)
                    duration_sec = total_samples / self._sample_rate
                    if duration_sec >= 0.35:
                        logger.info(f"VAD: End of speech chunk ({duration_sec:.2f}s). Processing...")
                        full_audio = np.concatenate(speech_buffer)
                        speech_buffer = []
                        self._process_speech_chunk(full_audio)
                    else:
                        speech_buffer = []

    def _process_speech_chunk(self, audio_data: np.ndarray):
        """Transcribes speech and matches wake-words."""
        model = self.init_whisper()
        if model is None:
            return

        try:
            segments, info = model.transcribe(
                audio_data,
                beam_size=1,
                language="en",
                vad_filter=True,
            )
            text = " ".join([s.text for s in segments]).strip()
            if not text or len(text) < 2:
                return

            logger.info(f"Native STT transcribed: '{text}'")

            has_wake = VoiceService.check_wake_word(text)
            clean_cmd = VoiceService.strip_wake_word(text) if has_wake else text

            if self._loop and not self._loop.is_closed():
                if has_wake:
                    logger.info(f"Wake word detected in: '{text}' -> Command: '{clean_cmd}'")
                    asyncio.run_coroutine_threadsafe(
                        broadcaster.broadcast(
                            event="wake_word_detected",
                            payload={"raw_text": text, "command": clean_cmd},
                        ),
                        self._loop,
                    )
                else:
                    asyncio.run_coroutine_threadsafe(
                        broadcaster.broadcast(
                            event="speech_transcribed",
                            payload={"text": text},
                        ),
                        self._loop,
                    )

        except Exception as e:
            logger.error(f"Error during audio chunk transcription: {e}")

    def speak(self, text: str):
        """Speaks text using OpenAI neural TTS (if key configured) or Windows SAPI in a worker thread."""
        t = threading.Thread(target=self._speak_worker, args=(text,), daemon=True)
        t.start()

    def _speak_worker(self, text: str):
        with self._tts_lock:
            self._current_speaking = True
            VoiceService._is_speaking = True
            if self._loop and not self._loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    broadcaster.broadcast(event="speech_started", payload={"text": text[:60]}),
                    self._loop,
                )

            # Try OpenAI neural TTS first if configured
            played_neural = False
            if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY.strip()) > 5:
                try:
                    from openai import OpenAI
                    import sounddevice as sd
                    import io
                    import soundfile as sf  # or wave

                    client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)
                    resp = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=text[:400],
                        response_format="wav",
                    )
                    audio_bytes = resp.read()
                    data, samplerate = sf.read(io.BytesIO(audio_bytes))
                    sd.play(data, samplerate)
                    sd.wait()
                    played_neural = True
                except Exception as e:
                    logger.info(f"OpenAI TTS fallback to SAPI: {e}")

            if not played_neural:
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    self._tts_engine = engine
                    engine.setProperty("rate", 185)
                    voices = engine.getProperty("voices")
                    for v in voices:
                        if "zira" in v.name.lower() or "david" in v.name.lower():
                            engine.setProperty("voice", v.id)
                            break
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    logger.warning(f"SAPI speech playback failed: {e}")

            self._current_speaking = False
            VoiceService._is_speaking = False
            self._tts_engine = None
            if self._loop and not self._loop.is_closed():
                asyncio.run_coroutine_threadsafe(
                    broadcaster.broadcast(event="speech_ended", payload={}),
                    self._loop,
                )

    def stop_speaking(self):
        """Halts active speech playback immediately."""
        VoiceService.interrupt_speech()
        self._current_speaking = False
        if self._tts_engine:
            try:
                self._tts_engine.stop()
            except Exception:
                pass


# Global singleton instance
native_audio = NativeAudioPipeline()
