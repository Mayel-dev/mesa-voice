from __future__ import annotations

import asyncio
import secrets

from fastapi import FastAPI, HTTPException, Request, Response
import httpx

from .audio import AudioError, MAX_INPUT_BYTES, decode_wav
from .config import Settings
from .pipeline import LocalPipeline, MockPipeline, NoSpeech, PipelineError


def create_app(settings: Settings | None = None, pipeline=None) -> FastAPI:
    settings = settings or Settings.from_env()
    pipeline = pipeline or (MockPipeline() if settings.mode == "mock" else LocalPipeline(settings))
    app = FastAPI(title="Mesa Voice", docs_url=None, redoc_url=None, openapi_url=None)
    busy = asyncio.Lock()
    app.state.pipeline_lock = busy

    @app.get("/healthz")
    async def health() -> dict:
        # Liveness only: not proof that models/audio/hardware work.
        return {"status": "ok", "mode": settings.mode, "protocol": 1}

    @app.post("/v1/voice")
    async def voice(request: Request) -> Response:
        supplied = request.headers.get("authorization", "")
        if not secrets.compare_digest(supplied.encode(), ("Bearer " + settings.token).encode()):
            raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "audio/wav":
            raise HTTPException(415, "Use audio/wav")
        length = request.headers.get("content-length")
        if length is not None:
            try:
                declared = int(length)
            except ValueError:
                raise HTTPException(400, "Invalid Content-Length") from None
            if declared < 0 or declared > MAX_INPUT_BYTES:
                raise HTTPException(413, "Audio too large")
        else:
            declared = None
        if busy.locked():
            raise HTTPException(503, "Busy", headers={"Retry-After": "2"})
        # No await between locked() and acquire(): one event loop / one worker.
        async with busy:
            data = bytearray()
            try:
                async with asyncio.timeout(10):
                    async for chunk in request.stream():
                        data.extend(chunk)
                        if len(data) > MAX_INPUT_BYTES:
                            raise HTTPException(413, "Audio too large")
            except TimeoutError:
                raise HTTPException(408, "Upload timeout") from None
            if declared is not None and len(data) != declared:
                raise HTTPException(400, "Content-Length mismatch")
            try:
                decode_wav(bytes(data))
            except AudioError as exc:
                raise HTTPException(422, str(exc)) from None
            try:
                async with asyncio.timeout(settings.pipeline_timeout):
                    reply = await pipeline.process(bytes(data))
                decode_wav(reply, minimum_seconds=0, maximum_seconds=20)
                if len(reply) <= 44:
                    raise PipelineError("Empty audio")
            except NoSpeech:
                raise HTTPException(422, "No speech detected") from None
            except (TimeoutError, httpx.TimeoutException):
                raise HTTPException(504, "Local inference timeout") from None
            except (PipelineError, AudioError, OSError, httpx.HTTPError):
                # Never return recordings, paths, model output or exception details.
                raise HTTPException(502, "Local inference failed") from None
        return Response(reply, media_type="audio/wav", headers={
            "Cache-Control": "no-store", "X-Mesa-Mode": settings.mode})

    return app
