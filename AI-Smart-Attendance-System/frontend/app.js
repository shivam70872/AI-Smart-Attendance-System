"use strict";

const $ = (id) => document.getElementById(id);
const state = { mode: "CHECK-IN", busy: false, timer: null, stream: null, lastMsg: {} };
const SCAN_EVERY_MS = 1500;

async function api(path, options = {}) {
  const res = await fetch(path, { credentials: "same-origin", ...options });
  let data = {};
  try { data = await res.json(); } catch (_) { /* file downloads have no JSON */ }
  if (!res.ok) {
    if (res.status === 401 && path !== "/api/login") showLogin();
    throw new Error(data.error || "Something went wrong. Please try again.");
  }
  return data;
}

/* ---------- views ---------- */
function showLogin() {
  stopCamera();
  $("app-view").hidden = true;
  $("login-view").hidden = false;
}

async function showApp(teacher) {
  $("login-view").hidden = true;
  $("app-view").hidden = false;
  $("teacher-info").textContent = `${teacher.name} · Class ${teacher.class_name}`;
  $("date").value = today();
  await loadRecords();
  startCamera();
}

const today = () => new Date().toLocaleDateString("en-CA"); // yyyy-mm-dd in local time

/* ---------- auth ---------- */
$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("login-error").textContent = "";
  try {
    const { teacher } = await api("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: $("username").value, password: $("password").value }),
    });
    $("password").value = "";
    showApp(teacher);
  } catch (err) {
    $("login-error").textContent = err.message;
  }
});

$("logout-btn").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" }).catch(() => {});
  showLogin();
});

/* ---------- camera + recognition ---------- */
async function startCamera() {
  const msg = $("camera-msg");
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    msg.textContent = "This browser can't use the camera. Open the app at http://localhost:5000 in Chrome, Edge or Firefox.";
    return;
  }
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
    $("video").srcObject = state.stream;
    msg.textContent = "";
    state.timer = setInterval(scan, SCAN_EVERY_MS);
  } catch (_) {
    msg.textContent = "Camera blocked. Allow camera access in your browser's address bar, then reload.";
  }
}

function stopCamera() {
  clearInterval(state.timer);
  if (state.stream) state.stream.getTracks().forEach((t) => t.stop());
  state.stream = null;
  drawBoxes([]);
}

async function scan() {
  const video = $("video");
  if (state.busy || !video.videoWidth) return;
  state.busy = true;
  try {
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    const { faces } = await api("/api/recognize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: canvas.toDataURL("image/jpeg", 0.7), mode: state.mode }),
    });
    drawBoxes(faces);
    report(faces);
    if (faces.some((f) => f.logged)) loadRecords();
  } catch (err) {
    drawBoxes([]);
    pushFeed(err.message, "bad");
  } finally {
    state.busy = false;
  }
}

function drawBoxes(faces) {
  const canvas = $("overlay");
  canvas.width = canvas.clientWidth;
  canvas.height = canvas.clientHeight;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.lineWidth = 3;
  ctx.font = "600 15px 'IBM Plex Sans', sans-serif";
  faces.forEach((f) => {
    const x = f.box.x * canvas.width, y = f.box.y * canvas.height;
    const w = f.box.w * canvas.width, h = f.box.h * canvas.height;
    const color = !f.roll_no ? "#c93c3c" : f.logged ? "#19c3ac" : "#e0a100";
    ctx.strokeStyle = color;
    ctx.strokeRect(x, y, w, h);
    const label = f.name ? `${f.name} ${f.confidence}%` : "Unknown";
    const tw = ctx.measureText(label).width + 12;
    ctx.fillStyle = color;
    ctx.fillRect(x, y + h, tw, 24);
    ctx.fillStyle = "#fff";
    ctx.fillText(label, x + 6, y + h + 17);
  });
}

function report(faces) {
  const now = Date.now();
  faces.forEach((f) => {
    const who = f.name || "Unknown face";
    const text = `${who}: ${f.message}`;
    const last = state.lastMsg[who];
    // Don't repeat the same message every scan; show it again after 10 seconds.
    if (last && last.text === text && now - last.at < 10000) return;
    state.lastMsg[who] = { text, at: now };
    pushFeed(text, f.logged ? "ok" : f.roll_no ? "warn" : "bad");
  });
}

function pushFeed(text, kind) {
  const feed = $("feed");
  feed.querySelectorAll(".muted").forEach((n) => n.remove());
  const li = document.createElement("li");
  li.className = kind;
  li.textContent = `${new Date().toLocaleTimeString()}  ${text}`;
  feed.prepend(li);
  while (feed.children.length > 5) feed.lastChild.remove();
}

/* ---------- mode toggle ---------- */
function setMode(mode) {
  state.mode = mode;
  const isIn = mode === "CHECK-IN";
  $("mode-in").classList.toggle("active", isIn);
  $("mode-out").classList.toggle("active", !isIn);
  $("mode-in").setAttribute("aria-checked", String(isIn));
  $("mode-out").setAttribute("aria-checked", String(!isIn));
}
$("mode-in").addEventListener("click", () => setMode("CHECK-IN"));
$("mode-out").addEventListener("click", () => setMode("CHECK-OUT"));

/* ---------- records ---------- */
async function loadRecords() {
  try {
    const data = await api(`/api/attendance?date=${encodeURIComponent($("date").value || today())}`);
    $("stat-present").textContent = data.present;
    $("stat-total").textContent = data.total_students;
    const body = $("rows");
    body.replaceChildren();
    data.records.forEach((r) => {
      const tr = document.createElement("tr");
      [r.roll_no, r.name].forEach((v) => tr.appendChild(cell(v)));
      const status = document.createElement("td");
      const pill = document.createElement("span");
      pill.className = "pill " + (r.status === "CHECK-IN" ? "in" : "out");
      pill.textContent = r.status === "CHECK-IN" ? "Checked in" : "Checked out";
      status.appendChild(pill);
      tr.appendChild(status);
      tr.appendChild(cell(r.time));
      body.appendChild(tr);
    });
    $("empty").hidden = data.records.length > 0;
  } catch (err) {
    pushFeed(err.message, "bad");
  }
}
function cell(text) {
  const td = document.createElement("td");
  td.textContent = text; // textContent, never innerHTML: names can't inject markup
  return td;
}
$("date").addEventListener("change", loadRecords);

$("export-btn").addEventListener("click", async () => {
  try {
    const res = await fetch(`/api/export?date=${encodeURIComponent($("date").value || today())}`, { credentials: "same-origin" });
    if (!res.ok) throw new Error((await res.json()).error || "Export failed.");
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `Attendance_${$("date").value || today()}.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (err) {
    pushFeed(err.message, "warn");
  }
});

/* ---------- add student ---------- */
const dialog = $("add-dialog");
$("add-btn").addEventListener("click", () => { $("add-error").textContent = ""; dialog.showModal(); });
$("add-cancel").addEventListener("click", () => dialog.close());
$("add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("add-error").textContent = "";
  try {
    await api("/api/students", { method: "POST", body: new FormData($("add-form")) });
    $("add-form").reset();
    dialog.close();
    pushFeed("Student saved. They can check in now.", "ok");
    loadRecords();
  } catch (err) {
    $("add-error").textContent = err.message;
  }
});

/* ---------- boot ---------- */
(async function init() {
  try {
    const { teacher } = await api("/api/me");
    teacher ? showApp(teacher) : showLogin();
  } catch (_) {
    showLogin();
  }
})();
