// Course Sniper — background service worker (MV3)
// Runs on a chrome.alarms timer, checks every watched section against the
// Anteater API, and fires a desktop notification when a spot opens.
//
// Note: chrome.alarms has a 1-minute minimum, and it only fires while Chrome
// is running. That is the tradeoff for having no server.

import { checkSection, hasOpenSpot } from "./checker.js";

const ALARM_NAME = "course-sniper-check";
const CHECK_PERIOD_MINUTES = 1;
const DEFAULT_TERM = "2026 Fall";
const WEBREG_URL = "https://www.reg.uci.edu/cgi-bin/webreg2/Main";

// --- storage helpers ---------------------------------------------------------

async function getState() {
  const { watches = [], term = DEFAULT_TERM } = await chrome.storage.local.get([
    "watches",
    "term",
  ]);
  return { watches, term };
}

async function setWatches(watches) {
  await chrome.storage.local.set({ watches });
}

// --- alarm lifecycle ---------------------------------------------------------

function ensureAlarm() {
  chrome.alarms.get(ALARM_NAME, (alarm) => {
    if (!alarm) {
      chrome.alarms.create(ALARM_NAME, {
        periodInMinutes: CHECK_PERIOD_MINUTES,
        delayInMinutes: 0.1,
      });
    }
  });
}

async function initBadge() {
  const { watches } = await getState();
  updateBadge(watches);
}

chrome.runtime.onInstalled.addListener(() => {
  ensureAlarm();
  initBadge();
});
chrome.runtime.onStartup.addListener(() => {
  ensureAlarm();
  initBadge();
});

// Keep the badge in sync when the popup adds/removes a section.
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.watches) {
    updateBadge(changes.watches.newValue || []);
  }
});

// --- the check loop ----------------------------------------------------------

async function runCheck() {
  const { watches, term } = await getState();
  if (!watches.length) return;

  let changed = false;

  for (const w of watches) {
    const info = await checkSection(term, w.code);
    if (!info) {
      w.lastStatus = "unknown";
      changed = true;
      continue;
    }

    const open = hasOpenSpot(info);
    w.lastStatus = open ? "open" : "full";
    w.lastLabel = `${info.dept} ${info.course_number}`;
    w.enrolled = info.enrolled;
    w.max_capacity = info.max_capacity;
    changed = true;

    if (open && !w.notified) {
      notifyOpen(info);
      w.notified = true;
    } else if (!open && w.notified) {
      // Section filled back up — re-arm so the user gets pinged if it reopens.
      w.notified = false;
    }
  }

  if (changed) await setWatches(watches);
  updateBadge(watches);
}

// Red badge on the toolbar icon = how many watched sections are open right now.
// This works regardless of OS notification settings.
function updateBadge(watches) {
  const openCount = watches.filter((w) => w.lastStatus === "open").length;
  chrome.action.setBadgeBackgroundColor({ color: "#e74c3c" });
  chrome.action.setBadgeTextColor?.({ color: "#ffffff" });
  chrome.action.setBadgeText({ text: openCount ? String(openCount) : "" });
  chrome.action.setTitle({
    title: openCount
      ? `Course Sniper — ${openCount} spot(s) open!`
      : "Course Sniper",
  });
}

function notifyOpen(info) {
  const title = `🎯 Spot open: ${info.dept} ${info.course_number}`;
  const message =
    `${info.course_title}\n` +
    `Section ${info.section_code} — ${info.enrolled}/${info.max_capacity} enrolled.\n` +
    `Click to open WebReg.`;

  chrome.notifications.create(`spot-${info.section_code}-${Date.now()}`, {
    type: "basic",
    iconUrl: "icons/icon128.png",
    title,
    message,
    priority: 2,
    requireInteraction: true,
  });
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM_NAME) runCheck();
});

// Clicking a notification opens WebReg so the user can enroll immediately.
chrome.notifications.onClicked.addListener((notificationId) => {
  if (notificationId.startsWith("spot-")) {
    chrome.tabs.create({ url: WEBREG_URL });
    chrome.notifications.clear(notificationId);
  }
});

// --- popup messaging ---------------------------------------------------------
// The popup asks the worker to run a check now (e.g. right after adding a code).

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.type === "checkNow") {
    runCheck().then(() => sendResponse({ ok: true }));
    return true; // keep the message channel open for the async response
  }
  if (msg && msg.type === "verifySection") {
    checkSection(msg.term, msg.code).then((info) => {
      sendResponse({ ok: !!info, info: info || null });
    });
    return true;
  }
});

// Make sure the alarm exists whenever the worker spins up.
ensureAlarm();
