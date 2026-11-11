from __future__ import annotations

import asyncio
import json
import math
import os
from pathlib import Path
import struct
import sys

import httpx

from .audio import RATE, encode_wav, resample_piper
from .config import Settings


class PipelineError(RuntimeError):
    pass


class NoSpeech(PipelineError):
    pass


async def run_bounded(command: list[str], *, stdin: bytes = b"", limit: int,
                      timeout: float) -> bytes:
    """No shell; bound output; always reap subprocess on timeout/cancellation."""
    process = await asyncio.create_subprocess_exec(
        *command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL, env={**os.environ, "PYTHONUTF8": "1"})

    async def communicate() -> bytes:
        async def write_input() -> None:
            assert process.stdin is not None
            process.stdin.write(stdin)
            await process.stdin.drain()
            process.stdin.close()

        sender = asyncio.create_task(write_input())
        data = bytearray()
        try:
            assert process.stdout is not None
            while chunk := await process.stdout.read(65536):
                data.extend(chunk)
                if len(data) > limit:
                    raise PipelineError("Subprocess output exceeded limit")
            await sender
            if await process.wait() != 0:
                raise PipelineError("Local speech process failed")
            return bytes(data)
        finally:
            if not sender.done():
                sender.cancel()
            await asyncio.gather(sender, return_exceptions=True)

    try:
        return await asyncio.wait_for(communicate(), timeout)
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


class MockPipeline:
    async def process(self, wav: bytes) -> bytes:
        # Deliberately does not pretend to understand the recording.
        pcm = b"".join(struct.pack("<h", round(2500 * math.sin(2 * math.pi * 440 * n / RATE)))
                       for n in range(RATE // 4))
        return encode_wav(pcm)


class LocalPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        if not Path(settings.stt_model).is_dir():
            raise ValueError("STT_MODEL must point to a downloaded faster-whisper directory")
        model = Path(settings.piper_model)
        if not model.is_file():
            raise ValueError("PIPER_MODEL must point to a downloaded ONNX voice")
        config = json.loads(Path(str(model) + ".json").read_text(encoding="utf-8"))
        self.piper_rate = int(config["audio"]["sample_rate"])
        if not 8000 <= self.piper_rate <= 96000:
            raise ValueError("Unsupported Piper sample rate")

    async def process(self, wav: bytes) -> bytes:
        s = self.settings
        output = await run_bounded([sys.executable, "-m", "mesa_voice.worker",
                                    "--model", s.stt_model, "--language", s.stt_language],
                                   stdin=wav, limit=16_384, timeout=50)
        try:
            text = json.loads(output)["text"]
        except (ValueError, KeyError, TypeError) as exc:
            raise PipelineError("Invalid STT response") from exc
        if not isinstance(text, str) or not text.strip():
            raise NoSpeech("No speech detected")
        if len(text) > 2000:
            raise PipelineError("STT response exceeded limit")

        # One request, no history, no tools and no cloud credentials.
        async with httpx.AsyncClient(timeout=httpx.Timeout(55, connect=3), trust_env=False) as client:
            async with client.stream("POST", s.ollama_url.rstrip("/") + "/api/chat", json={
                "model": s.ollama_model, "stream": False,
                "messages": [
                    {"role": "system", "content": "Eres un asistente doméstico. Responde en español con una o dos frases breves, máximo 45 palabras. No controles dispositivos ni afirmes haber ejecutado acciones."},
                    {"role": "user", "content": text}],
                "options": {"num_predict": 100, "temperature": 0.3},
            }) as response:
                response.raise_for_status()
                payload = bytearray()
                async for chunk in response.aiter_bytes():
                    payload.extend(chunk)
                    if len(payload) > 65_536:
                        raise PipelineError("LLM response exceeded limit")
        try:
            reply = json.loads(payload)["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise PipelineError("Invalid LLM response") from exc
        if not isinstance(reply, str) or not reply.strip():
            raise PipelineError("Empty LLM response")
        # Bound synthesis work and remove Piper's explicit phoneme delimiters.
        reply = reply.strip()[:400].replace("[[", "").replace("]]", "")
        raw = await run_bounded([*s.piper_command, "-m", s.piper_model, "--output-raw"],
                                stdin=(reply + "\n").encode("utf-8"),
                                limit=self.piper_rate * 2 * 60, timeout=30)
        return await asyncio.to_thread(resample_piper, raw, self.piper_rate)
