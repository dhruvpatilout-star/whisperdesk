"""
engine/transcriber.py

Thin wrapper around faster-whisper so both benchmark.py (Task 3) and
server.py (Task 2's backend) call the exact same code path. Keeping this
identical between benchmarking and the live app is what makes the
benchmark numbers meaningful for the A/B study.
"""

import time
from dataclasses import dataclass
from faster_whisper import WhisperModel

# Cache loaded models so repeated calls (benchmark loop, live server) don't
# reload weights from disk every time.
_MODEL_CACHE = {}


@dataclass
class TranscriptionResult:
    text: str
    audio_duration_s: float
    transcribe_time_s: float
    rtf: float  # real-time factor: transcribe_time / audio_duration (<1 = faster than real time)


def get_model(model_size: str = "base.en", compute_type: str = "int8") -> WhisperModel:
    key = (model_size, compute_type)
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = WhisperModel(model_size, device="cpu", compute_type=compute_type)
    return _MODEL_CACHE[key]


def transcribe_file(audio_path: str, model_size: str = "base.en", compute_type: str = "int8") -> TranscriptionResult:
    model = get_model(model_size, compute_type)

    start = time.perf_counter()
    segments, info = model.transcribe(audio_path, beam_size=1)
    text = " ".join(seg.text.strip() for seg in segments)
    elapsed = time.perf_counter() - start

    duration = info.duration if info.duration else elapsed
    rtf = elapsed / duration if duration > 0 else float("inf")

    return TranscriptionResult(
        text=text.strip(),
        audio_duration_s=duration,
        transcribe_time_s=elapsed,
        rtf=rtf,
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcriber.py <audio_file> [model_size]")
        sys.exit(1)
    path = sys.argv[1]
    size = sys.argv[2] if len(sys.argv) > 2 else "base.en"
    result = transcribe_file(path, size)
    print(f"Model: {size}")
    print(f"Text: {result.text}")
    print(f"Duration: {result.audio_duration_s:.2f}s | Transcribe time: {result.transcribe_time_s:.2f}s | RTF: {result.rtf:.3f}")
