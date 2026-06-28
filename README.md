# Course Sniper

A CLI tool that monitors UCI course sections for open spots and sends you an email notification the moment one becomes available.

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
python main.py config
```

During config, you'll set your term (e.g. `2026 Fall`) and email credentials. For Gmail, you need an [App Password](https://myaccount.google.com/apppasswords) (not your regular password).

## Usage

```bash
# Check a section's current status
python main.py check 34190

# Add sections to your watch list
python main.py add 34190
python main.py add 34191

# View your watch list with live status
python main.py list

# Remove a section
python main.py remove 34191

# Start monitoring (runs until Ctrl+C)
python main.py run
```

## Project Structure

```
course-sniper/
├── main.py          # CLI interface and monitoring loop
├── checker.py       # Anteater API + WebSOC scraper
├── notifier.py      # Email notifications via SMTP
├── config.json      # Your settings and watch list
├── requirements.txt # Python dependencies
└── REQUIREMENTS.md  # Software Requirements Specification
```

## Requirements

- Python 3.10+
- `requests` library
- Gmail account with App Password (or any SMTP-compatible email)
