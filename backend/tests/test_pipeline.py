"""Adapter tests use fake model outputs. They do not execute neural inference."""
import asyncio
import json
import struct

import httpx
import pytest

from mesa_voice.audio import decode_wav, encode_wav
from mesa_voice.config import Settings
from mesa_voice.pipeline import LocalPipeline, NoSpeech, PipelineError
import mesa_voice.pipeline as module


def make_pipeline(tmp_path):
    stt = tmp_path / "stt"
    stt.mkdir()
    voice = tmp_path / "voice.onnx"
    voice.write_bytes(b"fake model - never loaded")
    (tmp_path / "voice.onnx.json").write_text(json.dumps({"audio": {"sample_rate": 22050}}))
    return LocalPipeline(Settings(token="test-token-01234567890123456789012345678901",
                                  stt_model=str(stt), piper_model=str(voice)))


def test_local_adapter_contract_with_fake_models(tmp_path, monkeypatch):
    pipeline = make_pipeline(tmp_path)
    calls = []
    wav = encode_wav(b"\0\0" * 16000)

    async def fake_process(command, **kwargs):
        calls.append((command, kwargs))
        if "mesa_voice.worker" in command:
            assert kwargs["stdin"] == wav
            return json.dumps({"text": "¿Qué hora es?"}).encode()
        assert command[-1] == "--output-raw"
        assert kwargs["stdin"].decode() == "Respuesta de prueba.\n"
        return struct.pack("<h", 1000) * 22050

    def fake_ollama(request):
        body = json.loads(request.content)
        assert request.url == "http://127.0.0.1:11434/api/chat"
        assert body["stream"] is False
        assert body["messages"][1]["content"] == "¿Qué hora es?"
        assert "tools" not in body
        return httpx.Response(200, json={"message": {"content": "Respuesta de prueba."}})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(module, "run_bounded", fake_process)
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(fake_ollama), **kwargs))
    response = asyncio.run(pipeline.process(wav))
    assert len(decode_wav(response)) == 32000
    assert len(calls) == 2


@pytest.mark.parametrize("payload,error", [(b'{"text":""}', NoSpeech), (b"not-json", PipelineError)])
def test_bad_stt_does_not_call_llm(tmp_path, monkeypatch, payload, error):
    pipeline = make_pipeline(tmp_path)
    async def fake_process(*args, **kwargs):
        return payload
    def forbidden(**kwargs):
        raise AssertionError("LLM must not be called")
    monkeypatch.setattr(module, "run_bounded", fake_process)
    monkeypatch.setattr(module.httpx, "AsyncClient", forbidden)
    with pytest.raises(error):
        asyncio.run(pipeline.process(encode_wav(b"\0\0" * 16000)))
