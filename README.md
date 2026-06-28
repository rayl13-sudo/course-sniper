# Course Sniper

A website where UCI students enter their email and a section code, and get emailed when a spot opens up. No accounts, no login — just email + code.

Live at: *(add your URL after deploying)*

## How It Works

1. Enter your email once (saved in your browser).
2. Add 5-digit section codes from [UCI WebSOC](https://www.reg.uci.edu/perl/WebSoc).
3. The server checks all watched sections every 30 seconds via the [Anteater API](https://anteaterapi.com).
4. When a spot opens, you get an email with course details and a link to WebReg.
5. If the spot fills and re-opens later, you get emailed again.

Falls back to scraping WebSOC directly if the API is unavailable.

## Run Locally

```bash
pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000](http://localhost:5000).

For email notifications to work, set these environment variables before running:

```bash
export SMTP_EMAIL="your-gmail@gmail.com"
export SMTP_PASSWORD="your-gmail-app-password"
python app.py
```

To get a Gmail App Password: Google Account → Security → 2-Step Verification (enable first) → App Passwords → generate one.

## Deploy to Render (Free)

1. Push to GitHub.
2. Go to [render.com](https://render.com), click "New Web Service", connect the repo.
3. Render auto-detects `render.yaml`.
4. Set these environment variables on Render:
   - `SMTP_EMAIL` — your Gmail address
   - `SMTP_PASSWORD` — Gmail [App Password](https://myaccount.google.com/apppasswords)
5. Click Deploy. Share the URL with your friends.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SMTP_EMAIL` | Yes | Gmail address for sending notifications |
| `SMTP_PASSWORD` | Yes | Gmail App Password |
| `TERM` | No | UCI term, e.g. `2026 Fall` (default) |
| `SECRET_KEY` | No | Flask session key (auto-generated on Render) |

## Project Structure

```
course-sniper/
├── app.py               # Flask app, API routes, background monitor
├── models.py            # SQLAlchemy model (Watch)
├── checker.py           # Anteater API + WebSOC scraper
├── notifier.py          # Email via SMTP
├── main.py              # CLI (for local use)
├── templates/
│   └── index.html       # Single-page UI
├── render.yaml          # Render deployment config
├── Procfile             # Gunicorn config
├── requirements.txt     # Python dependencies
└── REQUIREMENTS.md      # Software Requirements Specification
```

## Tech Stack

Python, Flask, SQLAlchemy (SQLite), Anteater API, Gmail SMTP, Gunicorn, Render
