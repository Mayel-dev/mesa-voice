"""Send a canonical synthetic recording; response is not proof of speech recognition."""
import argparse
import os
from pathlib import Path

import httpx

from mesa_voice.audio import RATE, decode_wav, encode_wav

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8000")
parser.add_argument("--input", type=Path)
parser.add_argument("--output", type=Path, default=Path("reply.wav"))
args = parser.parse_args()
wav = args.input.read_bytes() if args.input else encode_wav(b"\0\0" * (RATE // 2))
decode_wav(wav)
response = httpx.post(args.url.rstrip("/") + "/v1/voice", content=wav,
                      headers={"Authorization": "Bearer " + os.environ["MESA_TOKEN"], "Content-Type": "audio/wav"},
                      timeout=150, trust_env=False)
response.raise_for_status()
decode_wav(response.content, minimum_seconds=0, maximum_seconds=20)
args.output.write_bytes(response.content)
print(f"HTTP {response.status_code}; {len(response.content)} bytes; mode={response.headers.get('x-mesa-mode')}")
