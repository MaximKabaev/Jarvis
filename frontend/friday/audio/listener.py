import time
import threading
from typing import Callable

import numpy as np
import sounddevice as sd

from friday.config import get_config
from friday.utils.logging import get_logger
from friday.utils.audio_utils import AudioBuffer

logger = get_logger(__name__)


class VADDetector:
    """Simple energy-based Voice Activity Detection"""

    def __init__(self, threshold: float = 0.01, aggressiveness: int = 2):
        self.threshold = threshold
        self.aggressiveness = aggressiveness
        self._speech_frames = 0
        self._silence_frames = 0
        self._required_speech_frames = 3
        self._required_silence_frames = 15 - (aggressiveness * 3)

    def is_speech(self, audio_frame: np.ndarray) -> bool:
        energy = np.sqrt(np.mean(audio_frame ** 2))
        return energy > self.threshold

    def process(self, audio_frame: np.ndarray) -> tuple[bool, bool]:
        """
        Returns: (is_speaking, should_stop)
        """
        is_speech = self.is_speech(audio_frame)

        if is_speech:
            self._speech_frames += 1
            self._silence_frames = 0
        else:
            self._silence_frames += 1

        # Consider speaking if we've had enough speech frames
        is_speaking = self._speech_frames >= self._required_speech_frames

        # Consider stopped if we've had enough silence after speaking
        should_stop = (
            is_speaking and
            self._silence_frames >= self._required_silence_frames
        )

        return is_speaking, should_stop

    def reset(self):
        self._speech_frames = 0
        self._silence_frames = 0


class AudioListener:
    def __init__(self):
        self.config = get_config()
        self._recording = False
        self._buffer = AudioBuffer(
            sample_rate=self.config.audio.sample_rate,
            max_duration=self.config.audio.max_recording_duration,
        )
        self._vad = VADDetector(
            aggressiveness=self.config.audio.vad_aggressiveness,
        )
        self._stream = None
        self._lock = threading.Lock()
        self._on_recording_complete: Callable[[np.ndarray], None] | None = None

    def start_recording(
        self,
        on_complete: Callable[[np.ndarray], None] | None = None,
    ):
        with self._lock:
            if self._recording:
                logger.warning("Already recording")
                return

            self._recording = True
            self._buffer.clear()
            self._vad.reset()
            self._on_recording_complete = on_complete
            self._start_time = time.time()

        logger.info("Recording started")
        self._start_stream()

    def stop_recording(self) -> np.ndarray | None:
        with self._lock:
            if not self._recording:
                return None

            self._recording = False
            audio_data = self._buffer.get_audio()
            self._buffer.clear()

        self._stop_stream()
        logger.info(f"Recording stopped, duration: {len(audio_data) / self.config.audio.sample_rate:.2f}s")

        return audio_data if len(audio_data) > 0 else None

    def _start_stream(self):
        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio status: {status}")

            if not self._recording:
                return

            audio_frame = indata.flatten().astype(np.float32)
            self._buffer.append(audio_frame)

            # Check VAD
            is_speaking, should_stop = self._vad.process(audio_frame)

            # Check duration limits
            elapsed = time.time() - self._start_time
            if elapsed < self.config.audio.min_recording_duration:
                return

            if elapsed >= self.config.audio.max_recording_duration:
                logger.info("Max recording duration reached")
                self._finish_recording()
                return

            if should_stop:
                logger.info("Silence detected, stopping recording")
                self._finish_recording()

        try:
            self._stream = sd.InputStream(
                samplerate=self.config.audio.sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=int(self.config.audio.sample_rate * 0.03),  # 30ms frames
                callback=audio_callback,
            )
            self._stream.start()
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            self._recording = False

    def _stop_stream(self):
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning(f"Error stopping stream: {e}")
            self._stream = None

    def _finish_recording(self):
        audio_data = self.stop_recording()
        if audio_data is not None and self._on_recording_complete:
            self._on_recording_complete(audio_data)

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def recording_duration(self) -> float:
        if self._recording:
            return time.time() - self._start_time
        return 0.0
