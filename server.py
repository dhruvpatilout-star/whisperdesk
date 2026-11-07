"""
server.py

Minimal backend for the Task 2 A/B study. Both client versions call the
SAME /transcribe endpoint, so any speed difference participants feel is
purely about how the UI reveals results, not about backend performance.

  Version A (live): client sends short rolling audio chunks; each chunk's
                     partial transcript is appended live (streaming feel).
  Version B (batched): client sends ONE full recording after "Stop" and
                        waits for the single final transcript.

Run:
  pip install flask flask-cors faster-whisper
  python server.py
Then open client/index.html in a browser (served via `python -m http.server`
from the client/ folder so the mic permission prompt works).

IMPORTANT: set WINNING_MODEL below to whatever Task 3 crowns the winner
(the brief predicts base.en, but use your actual results.json).
"""

import tempfile
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS

from engine.transcriber import transcribe_file

WINNING_MODEL = "base.en"  # <- update after Task 3 finishes

app = Flask(__name__)
CORS(app)


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "no audio file in request"}), 400

    audio_file = request.files["audio"]
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = transcribe_file(tmp_path, model_size=WINNING_MODEL)
        return jsonify({
            "text": result.text,
            "rtf": result.rtf,
            "transcribe_time_s": result.transcribe_time_s,
        })
    finally:
        Path(tmp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
