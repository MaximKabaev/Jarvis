import os
from pathlib import Path
from dataclasses import dataclass, field

import yaml


@dataclass
class CloudConfig:
    server_url: str = "http://localhost:8000"
    username: str = ""
    password: str = ""


@dataclass
class AudioConfig:
    wake_word: str = "friday"
    porcupine_access_key: str = ""
    sample_rate: int = 16000
    vad_aggressiveness: int = 2  # 0-3
    silence_duration: float = 1.5  # seconds of silence to end recording
    min_recording_duration: float = 0.5  # minimum recording length
    max_recording_duration: float = 30.0  # maximum recording length


@dataclass
class TTSConfig:
    model_path: str = ""
    speaker_id: int = 0
    length_scale: float = 1.0  # Speed: < 1.0 faster, > 1.0 slower


@dataclass
class STTConfig:
    model_size: str = "base"  # tiny, base, small, medium, large
    device: str = "cpu"  # cpu, cuda
    compute_type: str = "int8"  # int8, float16, float32


@dataclass
class LLMConfig:
    model: str = "llama3.2"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class Config:
    cloud: CloudConfig = field(default_factory=CloudConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Keyboard shortcut
    hotkey: str = "ctrl+shift+f"

    # Logging
    log_level: str = "INFO"
    log_file: str = ""

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "Config":
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        config_path = Path(config_path)

        if not config_path.exists():
            return cls()

        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls._from_dict(data)

    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        config = cls()

        if "cloud" in data:
            config.cloud = CloudConfig(**data["cloud"])
        if "audio" in data:
            config.audio = AudioConfig(**data["audio"])
        if "tts" in data:
            config.tts = TTSConfig(**data["tts"])
        if "stt" in data:
            config.stt = STTConfig(**data["stt"])
        if "llm" in data:
            config.llm = LLMConfig(**data["llm"])
        if "hotkey" in data:
            config.hotkey = data["hotkey"]
        if "log_level" in data:
            config.log_level = data["log_level"]
        if "log_file" in data:
            config.log_file = data["log_file"]

        # Override with environment variables
        config._apply_env_overrides()

        return config

    def _apply_env_overrides(self):
        if url := os.getenv("FRIDAY_SERVER_URL"):
            self.cloud.server_url = url
        if key := os.getenv("FRIDAY_PORCUPINE_KEY"):
            self.audio.porcupine_access_key = key
        if model := os.getenv("FRIDAY_LLM_MODEL"):
            self.llm.model = model


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reload_config(config_path: str | Path | None = None) -> Config:
    global _config
    _config = Config.load(config_path)
    return _config
