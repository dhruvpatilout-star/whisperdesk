// app.js
// Version is picked by URL: index.html?version=A  or  ?version=B
// (so each participant in the study just opens a different link)

const params = new URLSearchParams(window.location.search);
const VERSION = (params.get("version") || "A").toUpperCase();
const BACKEND = "http://localhost:5000/transcribe";
const CHUNK_MS = 2500; // how often Version A ships a chunk for "live" updates

const titleEl = document.getElementById("title");
const instructionsEl = document.getElementById("instructions");
const recordBtn = document.getElementById("record");
const statusEl = document.getElementById("status");
const cardEl = document.getElementById("card");

titleEl.textContent = `WhisperDesk — Version ${VERSION}`;
instructionsEl.textContent =
  VERSION === "A"
    ? "Live mode: words appear as you speak, in short rolling updates."
    : "Batched mode: nothing appears until you click Stop.";

let mediaRecorder, chunks = [], streamStart, liveTimer;
let recording = false;

recordBtn.onclick = async () => {
  if (!recording) {
    await startRecording();
  } else {
    stopRecording();
  }
};

async function startRecording() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  chunks = [];
  streamStart = performance.now();
  cardEl.textContent = "";
  recording = true;
  recordBtn.textContent = "Stop";
  recordBtn.classList.add("recording");
  statusEl.textContent = "Recording…";

  mediaRecorder.ondataavailable = (e) => chunks.push(e.data);

  if (VERSION === "A") {
    // Fire a transcription request every CHUNK_MS using whatever audio
    // has accumulated so far — this is the practical approximation of
    // "live streaming" with a non-streaming ASR backend.
    mediaRecorder.start();
    liveTimer = setInterval(sendLiveChunk, CHUNK_MS);
  } else {
    mediaRecorder.start();
  }
}

async function sendLiveChunk() {
  if (chunks.length === 0) return;
  const blob = new Blob(chunks, { type: "audio/webm" });
  const text = await sendToBackend(blob);
  if (text) cardEl.textContent = text; // replace with latest full-so-far transcript
}

function stopRecording() {
  recording = false;
  recordBtn.textContent = "Start Recording";
  recordBtn.classList.remove("recording");
  clearInterval(liveTimer);

  mediaRecorder.onstop = async () => {
    statusEl.textContent = "Finalizing…";
    const blob = new Blob(chunks, { type: "audio/webm" });
    const text = await sendToBackend(blob);
    cardEl.textContent = text || "(no speech detected)";
    statusEl.textContent = `Done in ${((performance.now() - streamStart) / 1000).toFixed(1)}s`;
  };
  mediaRecorder.stop();
}

async function sendToBackend(blob) {
  const form = new FormData();
  form.append("audio", blob, "clip.webm");
  try {
    const res = await fetch(BACKEND, { method: "POST", body: form });
    const data = await res.json();
    return data.text;
  } catch (err) {
    statusEl.textContent = "Backend error — is server.py running?";
    console.error(err);
    return null;
  }
}
