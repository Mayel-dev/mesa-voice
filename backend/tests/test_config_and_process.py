import asyncio
import sys

import pytest

from mesa_voice.config import Settings
from mesa_voice.pipeline import PipelineError, run_bounded

TOKEN = "test-token-01234567890123456789012345678901"


@pytest.mark.parametrize("kwargs", [
    {"token": "short"},
    {"token": "x" * 31},
    {"token": "á" * 32},
    {"mode": "unknown"},
    {"ollama_url": "https://external.example"},
    {"ollama_url": "http://127.0.0.1:11434/path"},
    {"ollama_url": "http://user:pass@127.0.0.1"},
    {"pipeline_timeout": 121},
    {"piper_command": ()},
])
def test_bad_configuration(kwargs):
    params = {"token": TOKEN, "mode": "mock", **kwargs}
    with pytest.raises(ValueError):
        Settings(**params)


def test_process_preserves_literal_shell_characters():
    literal = 'hello; $(echo bad) & "quoted"'
    result = asyncio.run(run_bounded([sys.executable, "-c", "import sys; sys.stdout.write(sys.argv[1])", literal], limit=100, timeout=5))
    assert result.decode() == literal


def test_process_output_limit():
    with pytest.raises(PipelineError):
        asyncio.run(run_bounded([sys.executable, "-c", "print('x'*10000)"], limit=100, timeout=5))


def test_process_timeout():
    with pytest.raises(TimeoutError):
        asyncio.run(run_bounded([sys.executable, "-c", "import time; time.sleep(30)"], limit=100, timeout=0.15))
