from __future__ import annotations

from dataclasses import dataclass
import json
import os
import sys
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    token: str
    mode: str = "local"
    stt_model: str = ""
    stt_language: str = "es"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    piper_model: str = ""
    piper_command: tuple[str, ...] = (sys.executable, "-m", "piper")
    pipeline_timeout: float = 115.0

    def __post_init__(self) -> None:
        if len(self.token) < 32 or any(ord(c) <= 32 or ord(c) > 126 for c in self.token):
            raise ValueError("MESA_TOKEN must contain at least 32 printable ASCII characters without spaces")
        if self.mode not in {"mock", "local"}:
            raise ValueError("MESA_MODE must be local or mock")
        url = urlsplit(self.ollama_url)
        if url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1", "::1"} or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
            raise ValueError("OLLAMA_URL must be an HTTP loopback origin")
        if not 1 <= self.pipeline_timeout <= 120:
            raise ValueError("Pipeline timeout must be 1..120 seconds")
        if not self.piper_command or not all(isinstance(v, str) and v for v in self.piper_command):
            raise ValueError("PIPER_COMMAND_JSON must be a nonempty JSON string array")
        if self.mode == "local" and (not self.stt_model or not self.piper_model):
            raise ValueError("Set local STT_MODEL and PIPER_MODEL paths")

    @classmethod
    def from_env(cls) -> "Settings":
        command = json.loads(os.environ.get("PIPER_COMMAND_JSON", json.dumps([sys.executable, "-m", "piper"])))
        if not isinstance(command, list):
            raise ValueError("PIPER_COMMAND_JSON must be an array")
        return cls(token=os.environ.get("MESA_TOKEN", ""),
                   mode=os.environ.get("MESA_MODE", "local"),
                   stt_model=os.environ.get("STT_MODEL", ""),
                   stt_language=os.environ.get("STT_LANGUAGE", "es"),
                   ollama_url=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"),
                   ollama_model=os.environ.get("OLLAMA_MODEL", "qwen2.5:3b"),
                   piper_model=os.environ.get("PIPER_MODEL", ""),
                   piper_command=tuple(command),
                   pipeline_timeout=float(os.environ.get("PIPELINE_TIMEOUT", "115")))
