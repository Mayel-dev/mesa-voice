import asyncio

from fastapi.testclient import TestClient
import httpx
import pytest

from mesa_voice.app import create_app
from mesa_voice.audio import RATE, decode_wav, encode_wav
from mesa_voice.config import Settings
from mesa_voice.pipeline import NoSpeech, PipelineError

TOKEN = "test-token-01234567890123456789012345678901"
HEADERS = {"Authorization": "Bearer " + TOKEN, "Content-Type": "audio/wav"}
WAV = encode_wav(b"\x00\x00" * (RATE // 2))


def app(pipeline=None):
    return create_app(Settings(token=TOKEN, mode="mock"), pipeline)


def test_health_and_mock_voice():
    client = TestClient(app())
    assert client.get("/healthz").json() == {"status": "ok", "mode": "mock", "protocol": 1}
    response = client.post("/v1/voice", headers=HEADERS, content=WAV)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["content-length"] == str(len(response.content))
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-mesa-mode"] == "mock"
    assert len(decode_wav(response.content)) == RATE // 4 * 2


@pytest.mark.parametrize("headers,status", [
    ({"Content-Type": "audio/wav"}, 401),
    ({**HEADERS, "Authorization": "Bearer wrong"}, 401),
    ({**HEADERS, "Content-Type": "audio/mpeg"}, 415),
    ({**HEADERS, "Content-Length": "300000"}, 413),
    ({**HEADERS, "Content-Length": "broken"}, 400),
    ({**HEADERS, "Content-Length": "44"}, 400),
])
def test_header_failures(headers, status):
    response = TestClient(app()).post("/v1/voice", headers=headers, content=WAV)
    assert response.status_code == status
    assert response.headers["content-type"] == "application/json"


def test_invalid_and_oversized_recordings():
    client = TestClient(app())
    assert client.post("/v1/voice", headers=HEADERS, content=b"invalid").status_code == 422
    assert client.post("/v1/voice", headers=HEADERS, content=encode_wav(b"\0\0" * (RATE * 8 + 1))).status_code == 413


@pytest.mark.parametrize("failure,status", [(NoSpeech("private"), 422),
    (PipelineError("private path and transcript"), 502), (TimeoutError(), 504)])
def test_pipeline_failures_are_sanitized(failure, status):
    class Broken:
        async def process(self, wav):
            raise failure
    response = TestClient(app(Broken())).post("/v1/voice", headers=HEADERS, content=WAV)
    assert response.status_code == status
    assert "private" not in response.text


def test_invalid_pipeline_output_rejected():
    class Broken:
        async def process(self, wav):
            return b"not a wav"
    assert TestClient(app(Broken())).post("/v1/voice", headers=HEADERS, content=WAV).status_code == 502


def test_second_concurrent_request_is_rejected_and_lock_released():
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        class Slow:
            async def process(self, wav):
                entered.set()
                await release.wait()
                return WAV
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app(Slow())), base_url="http://test") as client:
            first = asyncio.create_task(client.post("/v1/voice", headers=HEADERS, content=WAV))
            await asyncio.wait_for(entered.wait(), 2)
            second = await client.post("/v1/voice", headers=HEADERS, content=WAV)
            assert second.status_code == 503
            assert second.headers["retry-after"] == "2"
            release.set()
            assert (await first).status_code == 200
            assert (await client.post("/v1/voice", headers=HEADERS, content=WAV)).status_code == 200
    asyncio.run(run())


def test_total_timeout_cancels_processing_and_unlocks():
    async def run():
        cancelled = asyncio.Event()
        class Never:
            async def process(self, wav):
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.set()
        instance = create_app(Settings(token=TOKEN, mode="mock", pipeline_timeout=1), Never())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=instance), base_url="http://test") as client:
            result = await client.post("/v1/voice", headers=HEADERS, content=WAV)
            assert result.status_code == 504
            assert cancelled.is_set()
            assert not instance.state.pipeline_lock.locked()
    asyncio.run(run())
