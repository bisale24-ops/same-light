"use strict";

const KEY = "samelight.v1";
const CALLS = {
  better: "Real improvement",
  worse: "Real decline",
  noise: "Within noise",
  retake: "Retake — light too different",
  uncertain: "Can't certify — bigger light gap than measured",
};
const $ = (sel, root = document) => root.querySelector(sel);
const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  }
  for (const kid of kids) if (kid != null) node.append(kid);
  return node;
};

/* ---------- state (this device only) ---------- */
function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; }
}
function save(state) {
  try { localStorage.setItem(KEY, JSON.stringify(state)); } catch { /* private mode: session only */ }
}
let state = load();
let samples = null;
async function getSamples() {
  if (!samples) samples = await fetch("samples.json").then((r) => r.json());
  return samples;
}

/* ---------- routing ---------- */
function go(name) {
  document.querySelectorAll("section.screen").forEach((s) => s.classList.toggle("active", s.id === name));
  if (location.hash !== "#" + name) history.replaceState(null, "", name === "home" ? location.pathname : "#" + name);
  if (name === "track") renderTrack();
  window.scrollTo({ top: 0, behavior: "smooth" });
}
document.addEventListener("click", (e) => {
  const target = e.target.closest("[data-go]");
  if (target) { e.preventDefault(); go(target.dataset.go); }
});
const fromHash = () => go((location.hash || "#home").slice(1) || "home");
window.addEventListener("load", fromHash);
window.addEventListener("hashchange", fromHash);

/* ---------- photos ---------- */
function readPhoto(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, 2000 / Math.max(img.width, img.height));
      const canvas = el("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(img.src);
      resolve(canvas.toDataURL("image/jpeg", 0.92));
    };
    img.onerror = () => reject(new Error("That file is not a photo we can read."));
    img.src = URL.createObjectURL(file);
  });
}
function thumb(dataUrl, size = 240) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const scale = size / Math.max(img.width, img.height);
      const canvas = el("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL("image/jpeg", 0.8));
    };
    img.src = dataUrl;
  });
}
function wireDrop(drop, onPhoto) {
  const input = $("input[type=file]", drop);
  drop.addEventListener("click", () => input.click());
  input.addEventListener("change", () => input.files[0] && take(input.files[0]));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault(); drop.classList.remove("over");
    if (e.dataTransfer.files[0]) take(e.dataTransfer.files[0]);
  });
  async function take(file) {
    try { show(await readPhoto(file)); } catch (err) { onPhoto(null, err.message); }
  }
  function show(dataUrl) {
    let img = $("img", drop);
    if (!img) { img = el("img", { alt: "Selected photo" }); drop.prepend(img); }
    img.src = dataUrl;
    onPhoto(dataUrl);
  }
  return show;
}

async function api(path, body) {
  const response = await fetch(path, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.message || "Something went wrong. Try again in a minute.");
  return data;
}

/* ---------- light swatches ---------- */
function swatch(fp) {
  const [r, g, b] = fp.mean.map((v) => Math.round(v));
  return el("span", { class: "swatch", style: `background: rgb(${r},${g},${b})`, title: `average face colour rgb(${r}, ${g}, ${b})` });
}

/* ---------- track ---------- */
let photo = null;
let lastCheckin = null;
const showTrackPhoto = wireDrop($("#drop"), (dataUrl, error) => {
  photo = dataUrl;
  $("#scan-btn").disabled = !dataUrl;
  alertBox("#alert", error);
});

function alertBox(sel, message) {
  const box = $(sel);
  box.textContent = message || "";
  box.classList.toggle("on", Boolean(message));
}
function busy(sel, on, text) {
  $(sel).classList.toggle("on", on);
  if (text && $("#working-text")) $("#working-text").textContent = text;
}

function steps() {
  const hasBase = Boolean(state.baseline);
  const n = (state.checkins || []).length;
  const box = $("#track-steps");
  box.replaceChildren(
    el("span", { class: "step " + (hasBase ? "done" : "on"), text: hasBase ? "Baseline ✓" : "1 · Baseline" }),
    el("span", { class: "step " + (hasBase ? "on" : ""), text: `2 · Weekly check-in${n ? ` (${n} done)` : ""}` }),
    el("span", { class: "step " + (n ? "on" : ""), text: "3 · Proof card" }),
  );
}

function renderTrack() {
  steps();
  const hasBase = Boolean(state.baseline);
  $("#product-field").hidden = hasBase;
  $("#track-title").textContent = hasBase ? "Weekly check-in" : "Start with a baseline photo";
  $("#track-lede").textContent = hasBase
    ? `Testing: ${state.product || "your routine"}. Take this photo where you took the baseline — Same Light matches whatever light is left over.`
    : "This is the light every future check-in will be matched to. Take it where you will take the next ones.";
  $("#scan-btn").textContent = hasBase ? "Check in" : "Scan my skin";
  renderHistory();
}

$("#scan-btn").addEventListener("click", async () => {
  if (!photo) return;
  alertBox("#alert");
  const baseline = state.baseline;
  busy("#working", true, baseline ? "Matching your baseline light, then scanning…" : "Scanning your skin…");
  $("#scan-btn").disabled = true;
  try {
    const result = await api("/api/scan", {
      image: photo,
      baseline: baseline ? { fingerprint: baseline.fingerprint, scores: baseline.scores } : null,
    });
    const small = await thumb(photo);
    if (!baseline) {
      state = { product: $("#product").value.trim(), baseline: { ...pick(result), date: Date.now(), thumb: small }, checkins: [] };
    } else if (!result.retake) {
      state.checkins = [...(state.checkins || []), { ...pick(result), light: result.light, light_words: result.light_words, verdict: result.verdict, date: Date.now(), thumb: small }];
    }
    save(state);
    lastCheckin = baseline && !result.retake ? { image: photo, baseline: { scores: baseline.scores } } : null;
    renderResult(result, !baseline);
    renderTrack();
  } catch (err) {
    alertBox("#alert", err.message);
  } finally {
    busy("#working", false);
    $("#scan-btn").disabled = !photo;
  }
});

function pick(result) {
  return { fingerprint: result.fingerprint, scores: result.scores, overall: result.overall, skin_age: result.skin_age };
}

function overlayGrid(overlays) {
  const names = { wrinkle: "Wrinkles", pore: "Pores", texture: "Texture", acne: "Blemishes" };
  const figs = Object.entries(overlays || {}).map(([k, src]) =>
    el("figure", {}, el("img", { src, alt: `${names[k]} detected by YouCam`, loading: "lazy" }), el("figcaption", { text: names[k] })));
  return figs.length ? el("div", { class: "overlays" }, ...figs) : null;
}

function verdictRows(rows) {
  return el("div", { class: "verdicts" }, ...rows.map((row) => {
    const span = 20; // the bar covers ±10 points
    const pos = row.delta == null ? 50 : Math.max(0, Math.min(100, 50 + (row.delta / span) * 100));
    const bandW = (row.band * 2 / span) * 100;
    const bar = el("div", { class: "bandbar", title: `noise band ±${row.band}` },
      el("span", { class: "band", style: `left:${50 - bandW / 2}%;width:${bandW}%` }),
      row.delta == null ? null : el("span", { class: "dot", style: `left:${pos}%` }));
    const delta = row.delta == null ? "—" : (row.delta > 0 ? "+" : "") + row.delta;
    return el("div", { class: "verdict" },
      el("div", {}, el("strong", { text: row.label }), bar),
      el("div", { class: "scores", text: `${row.before ?? "—"} → ${row.after ?? "—"}  (${delta}, noise ±${row.band})` }),
      el("span", { class: "chip " + row.call, text: CALLS[row.call] }));
  }));
}

function renderResult(result, isBaseline, extra = {}) {
  const box = $("#result");
  box.hidden = false;
  const parts = [];
  if (isBaseline) {
    parts.push(el("h3", { text: "Baseline saved" + (extra.sample ? "" : "") }, extra.sample ? el("span", { class: "sample-tag", text: "sample" }) : null));
    parts.push(el("p", { class: "muted", text: `Overall ${result.overall} · skin age ${result.skin_age}. These are your reference scores; from now on the question is only whether they move more than the light and the scanner move on their own.` }));
    parts.push(scoreLine(result.scores));
  } else if (result.retake) {
    parts.push(el("h3", { text: "The light is too different to compare" }));
    parts.push(el("p", { class: "muted", text: `This photo is ${result.light_words}. Past that point matching is a guess, so no verdict — retake it closer to your baseline setup.` }));
  } else {
    parts.push(el("h3", {}, "Check-in result", extra.sample ? el("span", { class: "sample-tag", text: "sample" }) : null));
    const base = state.baseline || extra.baseline;
    parts.push(el("div", { class: "light-card", style: "margin-top:14px" },
      el("div", { class: "swatches" }, swatch(base.fingerprint), el("span", { class: "caption", text: "→" }), swatch(result.fingerprint)),
      el("div", {}, el("strong", { text: "Light: " + result.light_words }), el("p", { class: "caption", style: "margin:4px 0 0", text: result.matched ? "Matched to your baseline before scanning." : "" }))));
    parts.push(verdictRows(result.verdict));
    if (!extra.sample && lastCheckin) {
      const holder = el("div", { style: "margin-top:16px" });
      const button = el("button", { class: "btn small", text: "What would a plain scan say?" });
      button.onclick = async () => {
        button.disabled = true;
        button.textContent = "Scanning the photo as shot…";
        try {
          const plain = await api("/api/plain", lastCheckin);
          holder.replaceChildren(plainBox(plain.verdict));
        } catch (err) {
          holder.replaceChildren(el("p", { class: "caption", text: err.message }));
        }
      };
      holder.append(button, el("span", { class: "caption", style: "margin-left:10px", text: "One extra scan of this photo without light matching." }));
      parts.push(holder);
    }
    if (extra.raw_verdict) {
      parts.push(plainBox(extra.raw_verdict));
    }
  }
  const grid = overlayGrid(result.overlays);
  if (grid) parts.push(el("p", { class: "caption", style: "margin-top:20px", text: "What the YouCam scan detected on this photo:" }), grid);
  box.replaceChildren(el("div", { class: "card", style: "margin-top:28px" }, ...parts));
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}

function plainBox(rows) {
  const fooled = rows.filter((r) => r.call !== "noise");
  const said = fooled.length
    ? fooled.map((r) => `${r.label.toLowerCase()} ${CALLS[r.call].toLowerCase()} (${r.delta > 0 ? "+" : ""}${r.delta})`).join(", ") + "."
    : "no change either — here the light moved too little to fool it.";
  return el("div", { class: "card white", style: "margin-top:16px" },
    el("strong", { text: "Scanned as shot, without light matching, this check-in would have said:" }),
    el("p", { class: "muted", style: "margin:6px 0 0", text: said + (fooled.length ? " Same Light's verdict above is what survives once the light is equal." : "") }));
}

function scoreLine(scores) {
  const names = { wrinkle: "Wrinkles", pore: "Pores", texture: "Texture", acne: "Blemishes" };
  return el("div", { class: "facts", style: "margin-top:16px;grid-template-columns:repeat(4,1fr)" },
    ...Object.entries(scores).map(([k, v]) => el("div", { class: "card white fact" }, el("div", { class: "num", style: "font-size:34px", text: v }), el("p", { class: "caption", style: "margin:0", text: names[k] }))));
}

function renderHistory() {
  const box = $("#history");
  if (!state.baseline) { box.hidden = true; return; }
  box.hidden = false;
  const items = [el("div", { class: "tl-item" }, el("span", { text: "Baseline" }), el("span", { class: "mono", text: new Date(state.baseline.date).toLocaleDateString() }))];
  for (const c of state.checkins || []) {
    const real = (c.verdict || []).filter((r) => r.call === "better" || r.call === "worse");
    items.push(el("div", { class: "tl-item" },
      el("span", { text: real.length ? real.map((r) => `${r.label} ${CALLS[r.call].toLowerCase()}`).join(", ") : "No change beyond noise" }),
      el("span", { class: "mono", text: new Date(c.date).toLocaleDateString() })));
  }
  box.replaceChildren(el("div", { style: "margin-top:40px" },
    el("div", { class: "row", style: "justify-content:space-between" }, el("h3", { text: "Your history" }),
      el("div", { class: "row" },
        (state.checkins || []).length ? el("button", { class: "btn primary small", id: "proof-btn", text: "Make proof card" }) : null,
        el("button", { class: "btn ghost small", id: "reset-btn", text: "Start over" }))),
    el("p", { class: "caption", text: "Stored on this device only." }),
    el("div", { class: "timeline", style: "margin-top:8px" }, ...items)));
  $("#reset-btn").onclick = () => { if (confirm("Delete your baseline and check-ins from this device?")) { state = {}; save(state); $("#result").hidden = true; renderTrack(); } };
  const proof = $("#proof-btn");
  if (proof) proof.onclick = proofCard;
}

/* ---------- proof card ---------- */
function proofCard() {
  const last = state.checkins[state.checkins.length - 1];
  const weeks = Math.max(1, Math.round((last.date - state.baseline.date) / (7 * 864e5)));
  const c = el("canvas");
  c.width = 1080; c.height = 1350;
  const g = c.getContext("2d");
  g.fillStyle = "#fdfcfc"; g.fillRect(0, 0, 1080, 1350);
  const grad = g.createRadialGradient(150, 150, 5, 170, 170, 70);
  grad.addColorStop(0, "#ffd9c7"); grad.addColorStop(0.45, "#ff4704"); grad.addColorStop(1, "#0447ff");
  g.fillStyle = grad; g.beginPath(); g.arc(170, 170, 60, 0, Math.PI * 2); g.fill();
  g.fillStyle = "#000"; g.font = "600 40px Inter, sans-serif"; g.fillText("Same Light", 260, 184);
  g.font = "300 72px Inter, sans-serif";
  wrap(g, state.product || "My routine", 100, 360, 880, 84);
  g.fillStyle = "#6b655d"; g.font = "400 34px Inter, sans-serif";
  g.fillText(`${weeks} week${weeks > 1 ? "s" : ""} · light matched to the baseline photo`, 100, 470);
  let y = 590;
  for (const row of last.verdict || []) {
    g.fillStyle = "#f5f3f1"; roundRect(g, 100, y - 58, 880, 110, 28); g.fill();
    g.fillStyle = "#000"; g.font = "500 40px Inter, sans-serif"; g.fillText(row.label, 140, y + 12);
    g.font = "400 34px JetBrains Mono, monospace"; g.fillStyle = "#44403b";
    g.fillText(`${row.before} → ${row.after}`, 470, y + 12);
    const colors = { better: ["#e3f1e8", "#1f7a4d"], worse: ["#f7e2df", "#b3261e"], noise: ["#ebe8e4", "#44403b"], retake: ["#fff1d6", "#7a4b00"], uncertain: ["#fff1d6", "#7a4b00"] }[row.call];
    const label = { better: "real", worse: "real decline", noise: "noise", retake: "retake", uncertain: "not certified" }[row.call];
    g.font = "500 32px Inter, sans-serif";
    const w = g.measureText(label).width + 48;
    g.fillStyle = colors[0]; roundRect(g, 940 - w, y - 26, w, 56, 28); g.fill();
    g.fillStyle = colors[1]; g.fillText(label, 940 - w + 24, y + 12);
    y += 140;
  }
  g.fillStyle = "#6b655d"; g.font = "400 28px Inter, sans-serif";
  wrap(g, "A change counts only when it beats the measured noise band for that concern. Scored with YouCam AI Skin Analysis.", 100, 1220, 880, 38);
  const url = c.toDataURL("image/png");
  const dialog = el("dialog", { class: "proof" },
    el("img", { src: url, alt: "Your Same Light proof card" }),
    el("div", { class: "row", style: "justify-content:flex-end;margin-top:14px" },
      el("button", { class: "btn ghost small", text: "Close" }),
      el("a", { class: "btn primary small", href: url, download: "same-light-proof.png", text: "Download" })));
  document.body.append(dialog);
  $("button", dialog).onclick = () => dialog.close();
  dialog.addEventListener("close", () => dialog.remove());
  dialog.showModal();
}
function wrap(g, text, x, y, width, lh) {
  const words = text.split(" "); let line = "";
  for (const w of words) {
    const test = line ? line + " " + w : w;
    if (g.measureText(test).width > width && line) { g.fillText(line, x, y); line = w; y += lh; } else line = test;
  }
  g.fillText(line, x, y);
}
function roundRect(g, x, y, w, h, r) {
  g.beginPath(); g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
  g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
}

/* ---------- samples (real results, recorded; no API units spent) ---------- */
$("#sample-btn").addEventListener("click", async () => {
  const s = await getSamples();
  alertBox("#alert");
  if (!state.baseline || state.baseline.sample) {
    state = { product: "Sample: evening retinol", baseline: { ...s.track.baseline, date: Date.now() - 28 * 864e5, sample: true }, checkins: [] };
    showTrackPhoto(s.track.checkin_photo);
    photo = null; $("#scan-btn").disabled = true;
    const checkin = s.track.checkin;
    state.checkins.push({ ...pick(checkin), light: checkin.light, light_words: checkin.light_words, verdict: checkin.verdict, date: Date.now(), sample: true });
    save(state);
    renderTrack();
    renderResult(checkin, false, { sample: true, baseline: state.baseline, raw_verdict: s.track.raw_verdict });
  } else {
    alertBox("#alert", "You already have your own baseline. Use “Start over” below to try the sample.");
  }
});

/* ---------- guided camera: YouCam JS Camera Kit ---------- */
let kitReady = null;
function loadKit() {
  if (kitReady) return kitReady;
  kitReady = new Promise((resolve, reject) => {
    window.ymkAsyncInit = () => resolve(window.YMK);
    const s = el("script", { src: "https://plugins-media.makeupar.com/v2.2-camera-kit/sdk.js", async: "" });
    s.onerror = () => reject(new Error("The guided camera could not load. Upload a photo instead."));
    document.head.append(s);
  });
  return kitReady;
}
$("#camera-btn").addEventListener("click", async () => {
  alertBox("#alert");
  try {
    const YMK = await loadKit();
    if (!window.__kitWired) {
      YMK.addEventListener("faceDetectionCaptured", (captured) => {
        const image = captured && captured.images && captured.images[0] && captured.images[0].image;
        if (!image) return;
        const src = typeof image === "string" ? (image.startsWith("data:") ? image : "data:image/jpeg;base64," + image) : URL.createObjectURL(image);
        YMK.close();
        toJpeg(src).then(showTrackPhoto);
      });
      YMK.addEventListener("cameraFailed", () => {
        YMK.close();
        alertBox("#alert", "The camera could not start here. Allow camera access, or upload a photo instead.");
      });
      window.__kitWired = true;
    }
    const width = Math.min(560, $("#capture").clientWidth);
    YMK.init({ faceDetectionMode: "skincare", imageFormat: "base64", language: "enu", width, height: Math.round(width * 4 / 3) });
    YMK.openCameraKit();
  } catch (err) {
    alertBox("#alert", err.message || "The guided camera needs camera permission. You can upload a photo instead.");
  }
});
function toJpeg(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const c = el("canvas"); c.width = img.width; c.height = img.height;
      c.getContext("2d").drawImage(img, 0, 0); resolve(c.toDataURL("image/jpeg", 0.92));
    };
    img.src = src;
  });
}

/* ---------- pair ---------- */
const pair = { before: null, after: null };
const showBefore = wireDrop($("#drop-before"), (d, e) => { pair.before = d; pairReady(e); });
const showAfter = wireDrop($("#drop-after"), (d, e) => { pair.after = d; pairReady(e); });
function pairReady(error) {
  $("#pair-btn").disabled = !(pair.before && pair.after);
  alertBox("#pair-alert", error);
}
$("#pair-btn").addEventListener("click", async () => {
  alertBox("#pair-alert");
  busy("#pair-working", true);
  $("#pair-btn").disabled = true;
  try {
    renderPair(await api("/api/pair", { before: pair.before, after: pair.after }));
  } catch (err) {
    alertBox("#pair-alert", err.message);
  } finally {
    busy("#pair-working", false);
    pairReady();
  }
});
$("#pair-sample").addEventListener("click", async () => {
  const s = await getSamples();
  showBefore(s.pair.before_photo); showAfter(s.pair.after_photo);
  renderPair(s.pair.result, true);
});

function renderPair(result, sample = false) {
  const claimed = result.rows.filter((r) => Math.abs(r.claimed) > r.band);
  const survived = result.rows.filter((r) => r.real);
  const unsure = result.rows.filter((r) => r.uncertain);
  const headline = unsure.length
    ? `The light in this pair differs more than Same Light has measured, so ${unsure.length === 1 ? "one change" : unsure.length + " changes"} can't be certified either way.`
    : claimed.length === 0
    ? "The pair shows no change beyond noise, with or without the light."
    : survived.length === 0
      ? "Every change in this pair disappears when the light is matched."
      : `${survived.length} of ${claimed.length} claimed change${claimed.length > 1 ? "s" : ""} survive${survived.length === 1 ? "s" : ""} the light match.`;
  const rows = result.rows.map((r) => {
    const fmt = (v) => (v > 0 ? "+" : "") + v;
    const share = Math.abs(r.claimed) > r.band ? Math.round((r.light_share || 0) * 100) : 0;
    return el("div", { class: "verdict" },
      el("div", {}, el("strong", { text: r.label }),
        el("div", { class: "share-bar", title: `${share}% explained by light` }, el("span", { style: `width:${share}%` }))),
      el("div", { class: "scores", text: `as shown ${fmt(r.claimed)} · same light ${fmt(r.same_light)}` }),
      r.uncertain
        ? el("span", { class: "chip uncertain", text: "Can't certify" })
        : el("span", { class: "chip " + (r.real ? (r.same_light > 0 ? "better" : "worse") : "noise"), text: r.real ? "Real" : Math.abs(r.claimed) > r.band ? `${share}% light` : "No change" }));
  });
  const box = $("#pair-result");
  box.hidden = false;
  box.replaceChildren(el("div", { class: "card", style: "margin-top:28px" },
    el("h3", {}, headline, sample ? el("span", { class: "sample-tag", text: "sample" }) : null),
    el("p", { class: "muted", text: `The after photo is ${result.light_words}. The bar shows how much of each change the light alone accounts for.` }),
    el("div", { class: "verdicts" }, ...rows),
    el("p", { class: "caption", style: "margin-top:14px", text: "“As shown” compares the two photos as they are. “Same light” re-scans the after photo with its light matched to the before photo. Noise bands measured on three faces." })));
  box.scrollIntoView({ behavior: "smooth", block: "start" });
}
