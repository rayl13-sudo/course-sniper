#!/usr/bin/env python3
"""
Course Sniper — public web app

Anyone can enter their email + section code and get notified when a spot opens.
No accounts, no login.

Run locally:  python app.py
Production:   gunicorn app:app
"""

import os
import threading
import time
from collections import defaultdict
from datetime import datetime

from flask import Flask, render_template, request, jsonify

from models import db, Watch
from checker import check_section, has_open_spot
from notifier import send_email

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///course_sniper.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

TERM = os.environ.get("TERM", "2026 Fall")
CHECK_INTERVAL = 30
SMTP_EMAIL = os.environ.get("SMTP_EMAIL", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

# ---------------------------------------------------------------------------
# Monitor state
# ---------------------------------------------------------------------------

monitor_thread = None
monitor_running = False
monitor_log = []
MAX_LOG_ENTRIES = 100


def add_log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    monitor_log.append(f"[{timestamp}] {msg}")
    if len(monitor_log) > MAX_LOG_ENTRIES:
        monitor_log.pop(0)


# ---------------------------------------------------------------------------
# Background monitor
# ---------------------------------------------------------------------------

def monitor_loop():
    global monitor_running

    while monitor_running:
        with app.app_context():
            # Get all un-notified watches, grouped by section code
            watches = Watch.query.filter_by(notified=False).all()
            section_to_watches = defaultdict(list)
            for w in watches:
                section_to_watches[w.section_code].append(w)

            if not section_to_watches:
                add_log("No active watches")
                _sleep(CHECK_INTERVAL)
                continue

            add_log(f"Checking {len(section_to_watches)} section(s)")

            for code, watch_list in section_to_watches.items():
                if not monitor_running:
                    break

                info = check_section(TERM, code)
                if info is None:
                    add_log(f"WARN: Could not fetch {code}")
                    continue

                label = f"{info['dept']} {info['course_number']} ({code})"

                if has_open_spot(info):
                    add_log(f"OPEN: {label} — {info['enrolled']}/{info['max_capacity']}")

                    for w in watch_list:
                        if SMTP_EMAIL and SMTP_PASSWORD:
                            success = send_email(
                                "smtp.gmail.com", 587,
                                SMTP_EMAIL, SMTP_PASSWORD,
                                w.email, info,
                            )
                            if success:
                                add_log(f"EMAIL: Sent to {w.email} for {label}")
                            else:
                                add_log(f"ERROR: Failed to email {w.email}")

                        w.notified = True

                    db.session.commit()
                else:
                    add_log(f"FULL: {label} — {info['enrolled']}/{info['max_capacity']}")

            # Also reset watches where the section filled back up
            notified_watches = Watch.query.filter_by(notified=True).all()
            for w in notified_watches:
                info = check_section(TERM, w.section_code)
                if info and not has_open_spot(info):
                    w.notified = False
            db.session.commit()

        _sleep(CHECK_INTERVAL)


def _sleep(seconds):
    for _ in range(seconds):
        if not monitor_running:
            break
        time.sleep(1)


def ensure_monitor_running():
    global monitor_thread, monitor_running
    if monitor_running:
        return
    monitor_running = True
    add_log("Monitor started")
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", term=TERM)


@app.route("/api/log")
def api_log():
    return jsonify({"running": monitor_running, "log": monitor_log[-50:]})


@app.route("/api/watch", methods=["POST"])
def api_watch():
    data = request.json
    email = data.get("email", "").strip().lower()
    code = data.get("section_code", "").strip()

    if not email or "@" not in email:
        return jsonify({"ok": False, "error": "Enter a valid email address."}), 400

    if not code or len(code) != 5 or not code.isdigit():
        return jsonify({"ok": False, "error": "Section code must be 5 digits."}), 400

    # Verify the section exists
    info = check_section(TERM, code)
    if info is None:
        return jsonify({"ok": False, "error": f"Section {code} not found for {TERM}. Check the code."}), 400

    # Check for duplicate
    existing = Watch.query.filter_by(email=email, section_code=code).first()
    if existing:
        if existing.notified:
            existing.notified = False
            db.session.commit()
            return jsonify({"ok": True, "message": f"Re-watching {info['dept']} {info['course_number']}. We'll email you again when it opens."})
        return jsonify({"ok": False, "error": "You're already watching this section."}), 400

    watch = Watch(email=email, section_code=code)
    db.session.add(watch)
    db.session.commit()

    ensure_monitor_running()

    status = "OPEN" if has_open_spot(info) else "FULL"
    return jsonify({
        "ok": True,
        "message": f"Got it! Watching {info['dept']} {info['course_number']} — {info['course_title']} ({status}, {info['enrolled']}/{info['max_capacity']}). We'll email {email} when a spot opens.",
    })


@app.route("/api/check/<section_code>")
def api_check(section_code):
    info = check_section(TERM, section_code)
    if info:
        info["is_open"] = has_open_spot(info)
        return jsonify({"ok": True, "section": info})
    return jsonify({"ok": False, "error": f"Section {section_code} not found for {TERM}."})


@app.route("/api/unwatch", methods=["POST"])
def api_unwatch():
    data = request.json
    email = data.get("email", "").strip().lower()
    code = data.get("section_code", "").strip()

    watch = Watch.query.filter_by(email=email, section_code=code).first()
    if not watch:
        return jsonify({"ok": False, "error": "Not found."}), 404

    db.session.delete(watch)
    db.session.commit()
    return jsonify({"ok": True, "message": f"Removed {code}. You won't get emails for it anymore."})


@app.route("/api/my-watches", methods=["POST"])
def api_my_watches():
    """Look up watches by email — no auth needed, just email."""
    email = request.json.get("email", "").strip().lower()
    if not email:
        return jsonify({"ok": False, "error": "Enter your email."}), 400

    watches = Watch.query.filter_by(email=email).all()
    sections = []
    for w in watches:
        info = check_section(TERM, w.section_code)
        if info:
            info["is_open"] = has_open_spot(info)
            info["notified"] = w.notified
        sections.append(info or {"section_code": w.section_code, "error": True})

    return jsonify({"ok": True, "sections": sections})


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
