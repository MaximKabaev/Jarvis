import numpy as np

from friday.config import get_config
from friday.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechToText:
    def __init__(self):
        self.config = get_config()
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel

            logger.info(f"Loading Whisper model: {self.config.stt.model_size}")
            self._model = WhisperModel(
                self.config.stt.model_size,
                device=self.config.stt.device,
                compute_type=self.config.stt.compute_type,
            )
            logger.info("Whisper model loaded")
        except ImportError:
            logger.error("faster-whisper not installed. Run: pip install faster-whisper")
            raise
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        self._load_model()

        try:
            # Ensure audio is float32 and normalized
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Normalize if needed
            max_val = np.max(np.abs(audio_data))
            if max_val > 1.0:
                audio_data = audio_data / max_val

            segments, info = self._model.transcribe(
                audio_data,
                beam_size=5,
                language="en",  # Can be made configurable
                vad_filter=True,
            )

            # Combine all segments
            text = " ".join(segment.text.strip() for segment in segments)

            logger.debug(f"Transcribed: {text}")
            return text.strip()

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    def transcribe_file(self, audio_path: str) -> str:
        self._load_model()

        try:
            segments, info = self._model.transcribe(
                audio_path,
                beam_size=5,
                vad_filter=True,
            )

            text = " ".join(segment.text.strip() for segment in segments)
            return text.strip()

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""

    def unload_model(self):
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("Whisper model unloaded")
