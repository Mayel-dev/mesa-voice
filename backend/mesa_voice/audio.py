"""Strict RIFF/WAVE framing shared by server and tests; no decoder guesses."""
from __future__ import annotations

import io
import struct
import wave

RATE = 16_000
MAX_INPUT_BYTES = 44 + RATE * 2 * 8
MAX_OUTPUT_FRAMES = RATE * 20


class AudioError(ValueError):
    pass


def encode_wav(pcm: bytes) -> bytes:
    if len(pcm) % 2:
        raise AudioError("Odd PCM byte count")
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(pcm)
    return out.getvalue()


def decode_wav(data: bytes, *, minimum_seconds: float = 0.1,
               maximum_seconds: float = 8) -> bytes:
    """Accept only a canonical 44-byte PCM WAV header (the MCU writes this)."""
    if len(data) < 44:
        raise AudioError("Truncated WAV")
    riff, total, wave_id, fmt, fmt_len, encoding, channels, rate, byte_rate, align, bits, chunk, size = struct.unpack(
        "<4sI4s4sIHHIIHH4sI", data[:44])
    if (riff, wave_id, fmt, fmt_len, encoding, channels, rate, byte_rate,
            align, bits, chunk) != (b"RIFF", b"WAVE", b"fmt ", 16, 1, 1,
                                   RATE, RATE * 2, 2, 16, b"data"):
        raise AudioError("Expected canonical PCM16 mono 16000 Hz WAV")
    if total != len(data) - 8 or size != len(data) - 44 or size % 2:
        raise AudioError("WAV length mismatch")
    if not RATE * minimum_seconds <= size // 2 <= RATE * maximum_seconds:
        raise AudioError("Audio duration outside allowed range")
    return data[44:]


def resample_piper(raw: bytes, source_rate: int) -> bytes:
    """Anti-aliased resampling, 20 s bound, and 5 ms fade against hard edges."""
    import math
    import numpy as np
    from scipy.signal import resample_poly

    if not raw or len(raw) % 2 or not 8_000 <= source_rate <= 96_000:
        raise AudioError("Invalid Piper PCM output")
    audio = np.frombuffer(raw, dtype="<i2").astype(np.float64)
    common = math.gcd(source_rate, RATE)
    if source_rate != RATE:
        audio = resample_poly(audio, RATE // common, source_rate // common)
    audio = audio[:MAX_OUTPUT_FRAMES]
    if not audio.size:
        raise AudioError("Empty Piper output")
    fade = min(80, audio.size // 2)
    if fade:
        ramp = np.linspace(0.0, 1.0, fade)
        audio[:fade] *= ramp
        audio[-fade:] *= ramp[::-1]
    # Software headroom; acoustic loudness remains a hardware commissioning test.
    audio = np.clip(audio * 0.65, -24_000, 24_000).astype("<i2")
    return encode_wav(audio.tobytes())
