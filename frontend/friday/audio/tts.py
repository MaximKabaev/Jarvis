import io
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from friday.config import get_config
from friday.utils.logging import get_logger

logger = get_logger(__name__)


class TextToSpeech:
    def __init__(self):
        self.config = get_config()
        self._voice = None
        self._sample_rate = 22050  # Default Piper sample rate

    def _load_model(self):
        if self._voice is not None:
            return

        if not self.config.tts.model_path:
            logger.warning("No TTS model path configured, TTS will be disabled")
            return

        model_path = Path(self.config.tts.model_path)
        if not model_path.exists():
            logger.error(f"TTS model not found: {model_path}")
            return

        try:
            from piper import PiperVoice

            logger.info(f"Loading Piper model: {model_path}")
            self._voice = PiperVoice.load(str(model_path))
            self._sample_rate = self._voice.config.sample_rate
            logger.info("Piper model loaded")
        except ImportError:
            logger.error("piper-tts not installed. Run: pip install piper-tts")
        except Exception as e:
            logger.error(f"Failed to load Piper model: {e}")

    def speak(self, text: str, blocking: bool = True):
        logger.info(f"TTS speak called, text length: {len(text)}")
        audio_data = self.synthesize(text)
        if audio_data is not None:
            logger.info(f"Audio synthesized, {len(audio_data)} samples, playing...")
            self.play_audio(audio_data, blocking=blocking)
            logger.info("Audio playback finished")
        else:
            logger.warning("TTS synthesize returned None")

    def synthesize(self, text: str) -> np.ndarray | None:
        self._load_model()

        if self._voice is None:
            logger.warning("TTS not available, skipping synthesis")
            return None

        try:
            # Collect audio from synthesize generator
            audio_chunks = []
            for chunk in self._voice.synthesize(text):
                audio_chunks.append(chunk.audio_int16_bytes)

            if not audio_chunks:
                logger.warning("No audio generated")
                return None

            # Combine all chunks
            raw_audio = b"".join(audio_chunks)
            logger.info(f"Raw audio bytes: {len(raw_audio)}")

            # Convert to numpy array (16-bit signed integers)
            audio_data = np.frombuffer(raw_audio, dtype=np.int16).astype(np.float32) / 32768.0

            logger.info(f"Synthesized {len(audio_data)} audio samples")
            return audio_data

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return None

    def play_audio(self, audio_data: np.ndarray, blocking: bool = True):
        try:
            logger.info(f"Playing audio: {len(audio_data)} samples at {self._sample_rate}Hz")
            sd.play(audio_data, self._sample_rate)
            if blocking:
                sd.wait()
                logger.info("sd.wait() completed")
        except Exception as e:
            logger.error(f"Audio playback error: {e}")

    def stop(self):
        try:
            sd.stop()
        except Exception:
            pass

    def unload_model(self):
        if self._voice is not None:
            del self._voice
            self._voice = None
            logger.info("Piper model unloaded")

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def is_available(self) -> bool:
        self._load_model()
        return self._voice is not None


class MockTextToSpeech:
    """Mock TTS for testing without Piper"""

    def __init__(self):
        self._sample_rate = 22050

    def speak(self, text: str, blocking: bool = True):
        logger.info(f"[TTS] {text}")

    def synthesize(self, text: str) -> np.ndarray | None:
        logger.info(f"[TTS Synthesize] {text}")
        return None

    def play_audio(self, audio_data: np.ndarray, blocking: bool = True):
        pass

    def stop(self):
        pass

    def unload_model(self):
        pass

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def is_available(self) -> bool:
        return False
