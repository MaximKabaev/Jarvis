import io
from pathlib import Path
from collections import deque

import numpy as np
import sounddevice as sd

from friday.utils.logging import get_logger

logger = get_logger(__name__)


class AudioBuffer:
    def __init__(self, sample_rate: int = 16000, max_duration: float = 60.0):
        self.sample_rate = sample_rate
        self.max_samples = int(max_duration * sample_rate)
        self._buffer = deque(maxlen=self.max_samples)

    def append(self, audio_data: np.ndarray):
        for sample in audio_data.flatten():
            self._buffer.append(sample)

    def get_audio(self) -> np.ndarray:
        return np.array(self._buffer, dtype=np.float32)

    def clear(self):
        self._buffer.clear()

    def __len__(self):
        return len(self._buffer)

    @property
    def duration(self) -> float:
        return len(self._buffer) / self.sample_rate


def play_sound(sound_path: str | Path, blocking: bool = True):
    try:
        import soundfile as sf
        data, sample_rate = sf.read(str(sound_path))
        sd.play(data, sample_rate)
        if blocking:
            sd.wait()
    except Exception as e:
        logger.warning(f"Failed to play sound {sound_path}: {e}")


def play_audio(audio_data: np.ndarray, sample_rate: int = 22050, blocking: bool = True):
    try:
        sd.play(audio_data, sample_rate)
        if blocking:
            sd.wait()
    except Exception as e:
        logger.error(f"Failed to play audio: {e}")


def get_audio_devices():
    return sd.query_devices()


def get_default_input_device():
    return sd.query_devices(kind='input')


def get_default_output_device():
    return sd.query_devices(kind='output')
