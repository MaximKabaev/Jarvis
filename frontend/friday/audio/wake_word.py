import struct
import threading
from typing import Callable

import pvporcupine
import sounddevice as sd
import numpy as np

from friday.config import get_config
from friday.utils.logging import get_logger

logger = get_logger(__name__)


class WakeWordDetector:
    def __init__(self, callback: Callable[[], None] | None = None):
        self.config = get_config()
        self.callback = callback
        self._porcupine = None
        self._stream = None
        self._running = False
        self._thread = None

    def _initialize(self):
        if not self.config.audio.porcupine_access_key:
            raise ValueError("Porcupine access key not configured")

        try:
            # Try to use built-in keyword first
            self._porcupine = pvporcupine.create(
                access_key=self.config.audio.porcupine_access_key,
                keywords=[self.config.audio.wake_word],
            )
        except pvporcupine.PorcupineInvalidArgumentError:
            # If the wake word is not a built-in keyword, try custom keyword path
            logger.warning(f"'{self.config.audio.wake_word}' is not a built-in keyword, "
                          "please provide a custom keyword file path")
            raise

        logger.info(f"Wake word detector initialized for '{self.config.audio.wake_word}'")

    def start(self):
        if self._running:
            logger.warning("Wake word detector already running")
            return

        self._initialize()
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Wake word detection started")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None

        logger.info("Wake word detection stopped")

    def _listen_loop(self):
        frame_length = self._porcupine.frame_length

        def audio_callback(indata, frames, time_info, status):
            if status:
                logger.warning(f"Audio status: {status}")
            if not self._running:
                return

            # Convert to int16
            audio_frame = (indata.flatten() * 32767).astype(np.int16)

            # Process in frame-sized chunks
            if len(audio_frame) >= frame_length:
                pcm = audio_frame[:frame_length]
                keyword_index = self._porcupine.process(pcm)

                if keyword_index >= 0:
                    logger.info("Wake word detected!")
                    if self.callback:
                        self.callback()

        try:
            self._stream = sd.InputStream(
                samplerate=self._porcupine.sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=frame_length,
                callback=audio_callback,
            )
            self._stream.start()

            while self._running:
                sd.sleep(100)

        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
            self._running = False

    @property
    def is_running(self) -> bool:
        return self._running


class MockWakeWordDetector:
    """Mock detector for testing without Porcupine"""

    def __init__(self, callback: Callable[[], None] | None = None):
        self.callback = callback
        self._running = False

    def start(self):
        self._running = True
        logger.info("Mock wake word detector started (use hotkey to activate)")

    def stop(self):
        self._running = False
        logger.info("Mock wake word detector stopped")

    def trigger(self):
        if self.callback:
            self.callback()

    @property
    def is_running(self) -> bool:
        return self._running
