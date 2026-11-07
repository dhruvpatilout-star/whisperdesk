# WhisperDesk — Implementation Explainer

A plain-English walkthrough of what every piece does and *why* it was built
that way — so you can answer "walk me through your implementation" without
notes.

---

## 1. The big picture

WhisperDesk answers two separate questions:

- **Task 3 asks:** of three sizes of the same speech-recognition model,
  which one is the best trade-off between speed, accuracy, and memory on
  normal consumer hardware?
- **Task 2 asks:** once you have a transcription engine, does it feel
  better to users if words appear *live* as they speak, or if the full
  result appears *all at once* after they stop?

Task 3's winner literally becomes the engine powering Task 2's app — that's
why Task 3 has to run first. It's also why both tasks reuse the exact same
`transcriber.py` file: if the backend code were different between the
benchmark and the live app, you couldn't trust that the benchmark numbers
say anything about what users actually experienced.

---

## 2. Why faster-whisper

OpenAI's Whisper is the standard open speech-to-text model. `faster-whisper`
is a re-implementation of it (using a library called CTranslate2) that runs
significantly faster on CPU with no accuracy loss — which matters here
because the whole point is a *local* tool running on a normal laptop, not a
GPU server. This is why the engine imports `faster_whisper` rather than
OpenAI's original `whisper` package.

**If asked "why not just call an API (like OpenAI's own Whisper API)?"** —
because the project's premise is a *local* utility: no per-request cost, no
dependency on internet connectivity, and it's what makes Task 3 (comparing
model sizes for local hardware trade-offs) a meaningful question at all. An
API call has no "size vs. hardware" trade-off to measure.

---

## 3. Why these three model sizes (Task 3)

Whisper ships in several sizes (tiny → base → small → medium → large). Each
step up is roughly 2x the parameters, roughly 2x slower, and typically a
few percentage points more accurate. tiny/base/small was chosen because:

- `tiny.en` and `base.en` are the two realistic choices for "runs instantly
  on a laptop with no GPU."
- `small.en` represents "noticeably more accurate, but is it worth the
  latency cost?" — i.e., it's there to test whether the extra size is
  actually worth it, not because anyone expected it to win.
- The `.en` suffix means English-only versions, which are smaller and
  faster than the multilingual versions for the same accuracy, since the
  project only needs English.
- `int8` compute type (quantization) is used for all three — it shrinks
  the model's numbers from 32-bit to 8-bit precision, which roughly halves
  memory and speeds up inference, at a small, well-documented accuracy
  cost. It's used consistently across all three so the comparison stays
  fair — you're testing size vs. size, not quantized vs. unquantized.

**If asked "why not test medium/large too?"** — diminishing returns: past
`small.en`, latency on CPU gets bad enough that it stops being a realistic
option for a local real-time tool, so there's nothing left to debate.

---

## 4. The three metrics, explained

| Metric | What it actually measures | Why it matters here |
|---|---|---|
| **RTF (Real-Time Factor)** | `time to transcribe ÷ length of audio`. An RTF of 0.3 means a 10-second clip took 3 seconds to transcribe. | Below 1.0 means the model is faster than you're speaking — necessary for anything that feels "live." The brief's target of <0.3 is a conservative buffer. |
| **WER (Word Error Rate)** | The percentage of words the model got wrong (inserted, deleted, or substituted) compared to what was actually said. | Standard speech-recognition accuracy metric — lower is better. Computed here with the `jiwer` library, which implements the standard Levenshtein-distance-based formula rather than a hand-rolled one. |
| **Peak RAM (MB)** | The highest memory the Python process used during transcription, captured with `tracemalloc`. | A tiny laptop with 8GB RAM can't run a model that needs 4GB just for inference — this is the practical "will this even run" check. |

**Why P95 latency and not just average?** — averages hide bad outliers.
P95 answers "how slow is it on a bad run," which is the number that
actually determines whether the tool *feels* reliable, not just fast on
average.

---

## 5. The two UI versions, explained (Task 2)

- **Version A (live):** approximates real-time streaming by re-sending the
  growing audio clip to the backend every 2.5 seconds and replacing the
  displayed text with the latest full transcript. This is **not** true
  token-by-token streaming (which needs a model built for incremental
  decoding) — it's a practical approximation that still produces the
  visual effect of "words showing up while I talk," which is what the
  study is actually testing (the *feeling* of liveness, not the
  underlying architecture).
- **Version B (batched):** records silently, sends one full clip only
  after "Stop" is clicked, and shows the result once.

**Why mention this distinction to evaluators at all?** — being upfront
that Version A is an approximation (and explaining why) is exactly the
kind of "clear understanding of your own implementation" the brief is
asking for. It's a defensible, common real-world shortcut — just don't
imply it's literally streaming architecture if asked directly.

**Why the same backend for both?** — isolates the variable. Both versions
call the identical `/transcribe` endpoint and model; the only difference
is *when* the UI shows the result. That's what makes it a fair UI
experiment rather than confounding UI feel with backend speed.

---

## 6. File-by-file

- **`engine/transcriber.py`** — the one place that talks to faster-whisper.
  Loads and caches the model, times the transcription, computes RTF.
  Shared by the benchmark and the live server so both measure the same code.
- **`benchmarks/benchmark.py`** — loops over your 10 test clips × 3 model
  sizes, calls `transcriber.py` for each, computes RTF/WER/peak-RAM per
  sample, writes `results.json`, prints the summary table for the README.
- **`server.py`** — a small Flask API with one endpoint (`/transcribe`)
  that the client calls. Exists because browsers can't run Python directly
  — the client records audio, ships it here, gets text back.
- **`client/index.html` + `app.js`** — the participant-facing page. Reads
  `?version=A` or `?version=B` from the URL so each participant just opens
  a different link; records via the browser's `MediaRecorder` API; Version
  A also runs a 2.5s interval timer to simulate live updates.
- **`ground_truth.json`** — your own hand-written transcripts of the 10
  test clips, used as the "correct answer" for WER. This has to be
  something you typed yourself, since it's the reference the whole
  accuracy measurement depends on.

---

## 7. Likely questions, short answers

- **"Why local instead of cloud?"** — privacy, no cost-per-call, no
  internet dependency; also the only way "model size vs. hardware" is a
  real question to benchmark.
- **"How did you pick the sample size of 10 for both the audio test set
  and the user study?"** — it's the number specified in the brief for both
  tasks; small enough to run manually within the deadline, large enough to
  not be a single anecdote.
- **"What would you do with more time?"** — real incremental/streaming
  decoding for Version A instead of the chunked approximation, and testing
  medium/large models on GPU hardware.
- **"What's the single biggest limitation?"** — WER depends entirely on
  how carefully you transcribed your own `ground_truth.json`; any typo
  there directly distorts the accuracy numbers.
