# Course Sniper — Chrome Extension

Watch UCI course sections and get a **desktop notification** the moment a spot
opens. No server, no login, no email setup — everything runs inside your browser.

## Install (Load Unpacked)

1. Open `chrome://extensions` in Chrome.
2. Turn on **Developer mode** (top-right toggle).
3. Click **Load unpacked** and select this `extension/` folder.
4. Pin the 🎯 icon from the puzzle-piece menu so it's easy to reach.

To share it with friends, zip the `extension/` folder and have them repeat the
steps above. (Publishing to the Chrome Web Store is optional and costs a one-time
$5 developer fee — not required for personal/friend use.)

## Use

1. Click the 🎯 icon.
2. Type a 5-digit section code from
   [WebSOC](https://www.reg.uci.edu/perl/WebSoc) and hit **Add**.
3. Leave Chrome running. When a spot opens you get a notification — click it to
   jump straight to WebReg.

The list shows a live status dot: 🟢 open, 🔴 full, ⚪ checking.

## How it's different from the web-app version

| | Web app (Flask) | This extension |
|---|---|---|
| Needs a server | Yes (24/7) | **No** |
| Works when your computer is off | Yes | No — only while Chrome runs |
| Check interval | 30s | ~1 min (Chrome's minimum) |
| Alerts via | Email | Desktop notification |
| Cost | Server hosting | **Free** |

## Changing the term

Default is **2026 Fall**. To change it, open the extension's service worker
console (`chrome://extensions` → Course Sniper → *service worker*) and run:

```js
chrome.storage.local.set({ term: "2026 Winter" })
```

Valid quarters: `Fall`, `Winter`, `Spring`.

## Files

- `manifest.json` — MV3 config and permissions
- `background.js` — service worker; runs the `chrome.alarms` check loop
- `checker.js` — Anteater API client (ported from the Python `checker.py`)
- `popup.html` / `popup.js` — the UI
- `icons/` — extension icons
