from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_paths", nargs="+", type=Path)
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="ru")
    args = parser.parse_args()

    from faster_whisper import WhisperModel

    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    results = []
    for audio_path in args.audio_paths:
        segments, _info = model.transcribe(str(audio_path), language=args.language or None, vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments if segment.text and segment.text.strip())
        results.append({"path": str(audio_path), "text": " ".join(text.split())})
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
