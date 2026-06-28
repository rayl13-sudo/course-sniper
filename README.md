# Course Sniper

Monitors UCI course sections for open spots and notifies you the moment one becomes available. Works out of the box with browser notifications — no email setup required.

## Problem

UCI students get different enrollment windows. If yours is late, the classes you want are already full. Sometimes students drop later, but you'd have to keep refreshing WebSOC to catch it. Course Sniper automates that.

## How It Works

1. You add 5-digit section codes (from [UCI WebSOC](https://www.reg.uci.edu/perl/WebSoc)) to your watch list.
2. Course Sniper polls the [Anteater API](https://anteaterapi.com) every 30 seconds to check enrollment status.
3. When a section's status flips to OPEN, you get a browser notification popup and a sound alert.
4. If the spot fills again and re-opens later, it notifies you again.

Optionally, you can also set up Gmail email alerts (useful if you want notifications when the tab is closed). Falls back to scraping WebSOC directly if the API is unavailable.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000](http://localhost:5000). That's it — add section codes and hit Start.

Your browser will ask for notification permission on first visit. Allow it so you get popup alerts.

## Web UI

The web dashboard lets you:

- **Add/remove sections** — enter 5-digit codes from WebSOC
- **Quick check** — preview a section's status before adding it
- **Start/stop monitor** — watches your sections every 30 seconds
- **Browser notifications + sound** — alerts you immediately when a spot opens (works with zero config)
- **Email alerts (optional)** — collapsible section at the bottom if you also want email notifications

## CLI

Also available as a command-line tool:

```bash
python main.py config              # Set term and email
python main.py check 34190         # Quick-check a section
python main.py add 34190           # Add to watch list
python main.py remove 34190        # Remove from watch list
python main.py list                # View watch list with live status
python main.py run                 # Start monitoring (Ctrl+C to stop)
```

## Project Structure

```
course-sniper/
├── app.py               # Flask web app + background monitor
├── templates/
│   └── index.html       # Web UI (single page, dark theme)
├── main.py              # CLI interface
├── checker.py           # Anteater API + WebSOC scraper fallback
├── notifier.py          # Email notifications via SMTP
├── config.json          # Settings and watch list (git-ignored)
├── requirements.txt     # Python dependencies
└── REQUIREMENTS.md      # Software Requirements Specification
```

## Requirements

- Python 3.10+
- A modern browser (for notifications and sound alerts)
- Gmail with [App Password](https://myaccount.google.com/apppasswords) — only if you want email alerts
