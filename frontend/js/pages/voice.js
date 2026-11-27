// The core flow: choose language → record (max 30 s) → three transcripts → review → confirm and save.
import { api } from "../api.js";
import { html, toast, withBusy } from "../components.js";
import { state } from "../format.js";
import { renderOrderForm } from "../review.js";
import { bindSaveOrder } from "./orders.js";

const MAX_SECONDS = 30;
const OUTPUTS = [["original", "Original", "As spoken, in the original script"],
  ["roman", "Roman", "Same words in English letters"], ["english", "English", "Translation"]];
const STATUS_TEXT = { pending: "Waiting", processing: "Working…", done: "Ready", failed: "Failed" };
let recorder = null;
let timer = null;
let languagesCache = null;

export function stopVoice() {
  clearInterval(timer);
  if (recorder && recorder.state !== "inactive") { recorder.onstop = null; recorder.stop(); }
  if (recorder) recorder.stream.getTracks().forEach((t) => t.stop());
  recorder = null;
}

function pickMime() {
  return ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus"]
    .find((m) => window.MediaRecorder && MediaRecorder.isTypeSupported(m)) || "";
}

export async function renderVoice(app) {
  languagesCache = languagesCache || await api.get("/api/languages");
  const remembered = localStorage.getItem("voiceLanguage") || "unknown";
  const options = languagesCache.map((l) => `<option value="${l.code}" ${l.code === remembered ? "selected" : ""}>${html(l.name)}${l.status === "tested" ? " ✓ tested" : ""}</option>`).join("");
  const hours = state.retentionHours ?? 24;
  app.innerHTML = `
    <div class="page-head"><h1>New voice order</h1><p>Speak the order in any of 22 Indian languages or English.</p></div>
    ${state.sarvamConfigured ? "" : `<p class="notice warn">Voice needs a Sarvam API key on the server. <a href="#/orders/new">Type the order instead</a>.</p>`}
    <section class="card recorder-card">
      <div class="form-grid">
        <div class="field"><label for="lang">1. Language</label><select id="lang">${options}</select>
          <small>“Detect automatically” works for mixed Hindi-English too.</small></div>
        <div class="field consent"><label class="check"><input type="checkbox" id="consent"> 2. I understand the recording notice</label>
          <small>The audio is sent to <strong>Sarvam AI</strong> for speech-to-text. The recording is deleted as soon as all three texts are ready, or after ${hours} hours at most. Only the text is kept with the order. Ask the customer before recording them.</small></div>
      </div>
      <div class="mic-area">
        <button class="mic-btn" id="mic" aria-label="Start recording" ${state.sarvamConfigured ? "" : "disabled"}>
          <svg viewBox="0 0 24 24" width="44" height="44" aria-hidden="true"><path fill="currentColor" d="M12 15a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V22h2v-3.08A7 7 0 0 0 19 12h-2Z"/></svg>
        </button>
        <p class="mic-label" id="mic-label">3. Tap to record (max ${MAX_SECONDS} seconds)</p>
        <p class="timer" id="timer" aria-live="off">0:00 / 0:${MAX_SECONDS}</p>
      </div>
      <p class="muted cost-line">Each recording uses 3 Sarvam requests (original, Roman, English), about ₹0.49 for a 20-second order (₹0.49/min, before GST).</p>
    </section>
    <section id="results"></section>
    <div id="review"></div>`;

  const mic = app.querySelector("#mic");
  const consent = app.querySelector("#consent");
  app.querySelector("#lang").addEventListener("change", (e) => localStorage.setItem("voiceLanguage", e.target.value));
  mic.addEventListener("click", () => {
    if (recorder && recorder.state === "recording") { recorder.stop(); return; }
    if (!consent.checked) { toast("Please tick the recording notice first.", true); consent.focus(); return; }
    startRecording(app);
  });
}

async function startRecording(app) {
  const mic = app.querySelector("#mic");
  const label = app.querySelector("#mic-label");
  const timerEl = app.querySelector("#timer");
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    toast("This browser cannot record audio. Use Chrome, Edge or Firefox (on localhost or HTTPS).", true);
    return;
  }
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    toast("Microphone permission was denied. Allow the microphone in the browser and try again.", true);
    return;
  }
  const mime = pickMime();
  const chunks = [];
  recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
  const started = Date.now();
  recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  recorder.onstop = () => {
    clearInterval(timer);
    stream.getTracks().forEach((t) => t.stop());
    mic.classList.remove("recording");
    mic.setAttribute("aria-label", "Start recording");
    label.textContent = "Tap to record again";
    const seconds = (Date.now() - started) / 1000;
    recorder = null;
    if (seconds < 1) { toast("That was too short. Hold on a little longer.", true); return; }
    sendRecording(app, new Blob(chunks, { type: mime || "audio/webm" }), Math.min(seconds, MAX_SECONDS));
  };
  recorder.start();
  app.querySelector("#review").innerHTML = "";
  app.querySelector("#results").innerHTML = "";
  mic.classList.add("recording");
  mic.setAttribute("aria-label", "Stop recording");
  label.textContent = "Recording… tap to stop";
  timer = setInterval(() => {
    const s = Math.floor((Date.now() - started) / 1000);
    timerEl.textContent = `0:${String(s).padStart(2, "0")} / 0:${MAX_SECONDS}`;
    if (s >= MAX_SECONDS && recorder) recorder.stop();
  }, 250);
}

function renderResults(app, t) {
  const cards = OUTPUTS.map(([key, title, hint]) => {
    const status = t[`${key}_status`];
    const body = status === "done" ? html(t[`${key}_text`])
      : status === "failed" ? `<span class="error-text">${html(t[`${key}_error`] || "Failed")}</span>`
        : `<span class="muted">${STATUS_TEXT[status]}</span>`;
    const retry = status === "failed" ? `<button class="btn btn-small btn-secondary" data-retry="${key}">Retry ${title}</button>` : "";
    return `<div class="transcript status-${status}"><h3>${title} <span class="pill">${STATUS_TEXT[status]}</span></h3>
      <small class="muted">${hint}</small><p lang="${key === "original" ? (t.language_detected || "") : "en"}">${body}</p>${retry}</div>`;
  }).join("");
  const lang = t.language_detected ? ` · detected ${html(t.language_detected)}` : "";
  app.querySelector("#results").innerHTML = `<div class="card"><h2>What the customer said</h2>
    <div class="transcripts">${cards}</div>
    <p class="muted">${t.duration_seconds}s audio${lang} · Sarvam requests: ${t.request_count} of ${t.requests_planned} · est. ₹${t.cost_so_far_inr.toFixed(2)}
      · recording ${t.audio_stored ? "stored temporarily" : "deleted"}${t.reused ? " · same audio as before, nothing re-sent" : ""}</p></div>`;
  app.querySelectorAll("[data-retry]").forEach((b) => b.addEventListener("click", () =>
    withBusy(b, "Retrying…", async () => { await runOutput(app, t.id, b.dataset.retry); })));
}

async function runOutput(app, id, output) {
  try {
    const t = await api.post(`/api/transcriptions/${id}/outputs/${output}`);
    renderResults(app, t);
    return t;
  } catch (err) {
    toast(err.message, true);
    return null;
  }
}

async function sendRecording(app, blob, seconds) {
  const results = app.querySelector("#results");
  results.innerHTML = `<div class="card"><p class="processing">Sending to Sarvam… getting the original transcript first.</p></div>`;
  const form = new FormData();
  form.append("file", blob, "order.webm");
  form.append("language", app.querySelector("#lang").value);
  form.append("consent", "true");
  form.append("duration_seconds", seconds.toFixed(2));
  let t;
  try {
    t = await api.post("/api/transcriptions", form);
  } catch (err) {
    results.innerHTML = `<div class="card"><p class="error-text">${html(err.message)}</p></div>`;
    return;
  }
  renderResults(app, t);
  if (t.original_status !== "done") return;
  for (const output of ["roman", "english"]) {
    if (t[`${output}_status`] !== "done") t = (await runOutput(app, t.id, output)) || t;
  }
  await showReview(app, t);
}

async function showReview(app, t) {
  const slot = app.querySelector("#review");
  try {
    const draft = await api.post("/api/extract", {
      original: t.original_text,
      roman: t.roman_status === "done" ? t.roman_text : null,
      english: t.english_status === "done" ? t.english_text : null,
    });
    const flagged = draft.items.filter((i) => i.needs_review).length + Object.keys(draft.uncertain_fields).length;
    slot.innerHTML = `<div class="page-head"><h2>4. Check and correct</h2>
      <p>${flagged ? `${flagged} thing(s) need a look, marked <span class="badge badge-review">Check</span>.` : "Everything was understood. Please still check before saving."}</p></div>
      ${renderOrderForm(draft, "Confirm and save order")}`;
  } catch (err) {
    slot.innerHTML = `<p class="notice warn">Could not read the order automatically (${html(err.message)}). Fill it in below.</p>${renderOrderForm({}, "Confirm and save order")}`;
  }
  bindSaveOrder(slot.querySelector("#order-form"), () => ({ source: "voice", transcription_id: t.id }));
  slot.scrollIntoView({ behavior: "smooth", block: "start" });
}
