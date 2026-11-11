"""One-shot STT worker; a process boundary permits a real cancellation deadline."""
from __future__ import annotations

import argparse
import io
import json
import sys

from .audio import MAX_INPUT_BYTES, decode_wav


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--language", default="es")
    args = parser.parse_args()
    wav = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    decode_wav(wav)
    from faster_whisper import WhisperModel
    # Local path + local_files_only prevents silent runtime model downloads.
    model = WhisperModel(args.model, device="cpu", compute_type="int8", local_files_only=True)
    segments, _ = model.transcribe(io.BytesIO(wav), language=args.language,
                                    beam_size=1, vad_filter=True,
                                    condition_on_previous_text=False)
    text = " ".join(segment.text.strip() for segment in segments).strip()[:2000]
    sys.stdout.write(json.dumps({"text": text}, ensure_ascii=True))


if __name__ == "__main__":
    main()
