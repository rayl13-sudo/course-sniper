# Course Sniper

Monitors UCI course sections for open spots and emails you the moment one becomes available. Available as a web UI or CLI.

## Problem

UCI students get different enrollment windows. If yours is late, the classes you want are already full. Sometimes students drop later, but you'd have to keep refreshing WebSOC to catch it. Course Sniper automates that.

## How It Works

1. You add 5-digit section codes (from [UCI WebSOC](https://www.reg.uci.edu/perl/WebSoc)) to your watch list.
2. Course Sniper polls the [Anteater API](https://anteaterapi.com) every 30 seconds (configurable) to check enrollment status.
3. When a section's status flips to OPEN, it sends you an email with the course details and a direct link to WebReg.
4. If the spot fills again and re-opens later, it notifies you again.

Falls back to scraping WebSOC directly if the API is unavailable.

## Setup

```bash
pip install -r requirements.txt
```

For Gmail notifications, you need an [App Password](https://myaccount.google.com/apppasswords) (not your regular password).

## Web UI

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser. From there you can add/remove sections, configure email settings, start/stop the monitor, and see live logs.

## CLI

```bash
# Configure email and term
python main.py config

# Check a section's current status
python main.py check 34190

# Add/remove sections
python main.py add 34190
python main.py remove 34190

# View watch list with live status
python main.py list

# Start monitoring (runs until Ctrl+C)
python main.py run
```

## Project Structure

```
course-sniper/
├── app.py               # Flask web app
├── templates/
│   └── index.html       # Web UI (single page)
├── main.py              # CLI interface
├── checker.py           # Anteater API + WebSOC scraper
├── notifier.py          # Email notifications via SMTP
├── config.json          # Your settings and watch list
├── requirements.txt     # Python dependencies
└── REQUIREMENTS.md      # Software Requirements Specification
```

## Requirements

- Python 3.10+
- Gmail account with App Password (or any SMTP-compatible email)
