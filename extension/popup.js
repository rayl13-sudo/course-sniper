// Course Sniper — popup UI logic
// Manages the watch list in chrome.storage.local and talks to the background
// service worker to verify codes and trigger checks.

const DEFAULT_TERM = "2026 Fall";

const el = {
  code: document.getElementById("code"),
  addBtn: document.getElementById("addBtn"),
  msg: document.getElementById("msg"),
  list: document.getElementById("watches"),
  empty: document.getElementById("empty"),
  term: document.getElementById("term"),
  refreshBtn: document.getElementById("refreshBtn"),
};

async function getState() {
  const { watches = [], term = DEFAULT_TERM } = await chrome.storage.local.get([
    "watches",
    "term",
  ]);
  return { watches, term };
}

function setMsg(text, kind) {
  el.msg.textContent = text || "";
  el.msg.className = "msg" + (kind ? " " + kind : "");
}

function render(watches) {
  el.list.innerHTML = "";
  el.empty.style.display = watches.length ? "none" : "block";

  for (const w of watches) {
    const status = w.lastStatus || "unknown";
    const li = document.createElement("li");

    const dot = document.createElement("span");
    dot.className = "dot " + status;

    const info = document.createElement("div");
    info.className = "info";
    const code = document.createElement("div");
    code.className = "code";
    code.textContent = w.lastLabel ? `${w.lastLabel} · ${w.code}` : w.code;
    const sub = document.createElement("div");
    sub.className = "sub";
    if (status === "open") {
      sub.textContent = `OPEN — ${w.enrolled}/${w.max_capacity} · you'll be notified`;
    } else if (status === "full") {
      sub.textContent = `Full — ${w.enrolled}/${w.max_capacity}`;
    } else {
      sub.textContent = "Checking…";
    }
    info.append(code, sub);

    const rm = document.createElement("button");
    rm.className = "rm";
    rm.textContent = "✕";
    rm.title = "Remove";
    rm.addEventListener("click", () => removeWatch(w.code));

    li.append(dot, info, rm);
    el.list.append(li);
  }
}

async function refresh() {
  const { watches, term } = await getState();
  el.term.textContent = term;
  render(watches);
}

async function addWatch() {
  const code = el.code.value.trim();
  if (!/^\d{5}$/.test(code)) {
    setMsg("Section code must be exactly 5 digits.", "err");
    return;
  }

  const { watches, term } = await getState();
  if (watches.some((w) => w.code === code)) {
    setMsg("You're already watching that section.", "err");
    return;
  }

  setMsg("Verifying…", "");
  el.addBtn.disabled = true;

  let res;
  try {
    res = await chrome.runtime.sendMessage({ type: "verifySection", term, code });
  } catch {
    res = { ok: false };
  }
  el.addBtn.disabled = false;

  if (!res || !res.ok || !res.info) {
    setMsg(`Section ${code} not found for ${term}. Check the code.`, "err");
    return;
  }

  const info = res.info;
  watches.push({
    code,
    notified: false,
    lastStatus: null,
    lastLabel: `${info.dept} ${info.course_number}`,
    enrolled: info.enrolled,
    max_capacity: info.max_capacity,
  });
  await chrome.storage.local.set({ watches });
  el.code.value = "";
  setMsg(`Watching ${info.dept} ${info.course_number} — ${info.course_title}.`, "ok");

  chrome.runtime.sendMessage({ type: "checkNow" }).catch(() => {});
  refresh();
}

async function removeWatch(code) {
  const { watches } = await getState();
  await chrome.storage.local.set({ watches: watches.filter((w) => w.code !== code) });
  refresh();
}

el.addBtn.addEventListener("click", addWatch);
el.code.addEventListener("keydown", (e) => {
  if (e.key === "Enter") addWatch();
});
el.refreshBtn.addEventListener("click", async () => {
  setMsg("Checking all sections…", "");
  try {
    await chrome.runtime.sendMessage({ type: "checkNow" });
  } catch {}
  await refresh();
  setMsg("Updated.", "ok");
});

// React live to background updates while the popup is open.
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.watches) refresh();
});

refresh();
