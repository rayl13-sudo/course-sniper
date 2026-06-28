#!/usr/bin/env python3
"""
Course Sniper — Web UI

Run with: python app.py
Then open: http://localhost:5000
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from checker import check_section, has_open_spot
from notifier import send_email

app = Flask(__name__)

CONFIG_PATH = Path(__file__).parent / "config.json"

# Monitor state
monitor_thread = None
monitor_running = False
monitor_log = []  # Recent log entries
MAX_LOG_ENTRIES = 50


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {
        "email": {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "",
            "sender_password": "",
            "recipient_email": "",
        },
        "term": "2026 Fall",
        "check_interval_seconds": 30,
        "courses": [],
    }


def save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def add_log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    monitor_log.append(entry)
    if len(monitor_log) > MAX_LOG_ENTRIES:
        monitor_log.pop(0)


def monitor_loop():
    """Background thread that polls sections and sends notifications."""
    global monitor_running
    notified = set()

    while monitor_running:
        config = load_config()
        term = config["term"]
        email_cfg = config["email"]

        for code in config["courses"]:
            if not monitor_running:
                break

            info = check_section(term, code)
            if info is None:
                add_log(f"WARN: Could not fetch section {code}")
                continue

            label = f"{info['dept']} {info['course_number']} ({code})"

            if has_open_spot(info):
                if code not in notified:
                    add_log(f"OPEN: {label} — {info['enrolled']}/{info['max_capacity']} — sending email")
                    if email_cfg.get("sender_email") and email_cfg.get("sender_password"):
                        success = send_email(
                            email_cfg["smtp_server"],
                            email_cfg["smtp_port"],
                            email_cfg["sender_email"],
                            email_cfg["sender_password"],
                            email_cfg["recipient_email"],
                            info,
                        )
                        if success:
                            notified.add(code)
                            add_log(f"EMAIL: Notification sent for {label}")
                        else:
                            add_log(f"ERROR: Failed to send email for {label}")
                    else:
                        add_log(f"OPEN: {label} — email not configured, skipping notification")
                        notified.add(code)
                else:
                    add_log(f"OPEN: {label} — already notified")
            else:
                if code in notified:
                    notified.discard(code)
                add_log(f"FULL: {label} — {info['enrolled']}/{info['max_capacity']}")

        interval = config.get("check_interval_seconds", 30)
        for _ in range(interval):
            if not monitor_running:
                break
            time.sleep(1)


# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """Get current state: config, section statuses, monitor state, logs."""
    config = load_config()
    sections = []
    for code in config["courses"]:
        info = check_section(config["term"], code)
        if info:
            info["is_open"] = has_open_spot(info)
        sections.append(info or {"section_code": code, "error": True})

    return jsonify({
        "config": {
            "term": config["term"],
            "check_interval_seconds": config["check_interval_seconds"],
            "sender_email": config["email"].get("sender_email", ""),
            "recipient_email": config["email"].get("recipient_email", ""),
            "has_password": bool(config["email"].get("sender_password")),
        },
        "sections": sections,
        "monitor_running": monitor_running,
        "log": monitor_log[-20:],
    })


@app.route("/api/check/<section_code>")
def api_check(section_code):
    """Quick-check a section without adding it."""
    config = load_config()
    info = check_section(config["term"], section_code)
    if info:
        info["is_open"] = has_open_spot(info)
        return jsonify({"ok": True, "section": info})
    return jsonify({"ok": False, "error": f"Section {section_code} not found"})


@app.route("/api/add", methods=["POST"])
def api_add():
    code = request.json.get("section_code", "").strip()
    if not code or len(code) != 5 or not code.isdigit():
        return jsonify({"ok": False, "error": "Invalid section code. Must be 5 digits."}), 400

    config = load_config()
    if code in config["courses"]:
        return jsonify({"ok": False, "error": f"Section {code} already in watch list."}), 400

    config["courses"].append(code)
    save_config(config)
    return jsonify({"ok": True, "message": f"Added {code}"})


@app.route("/api/remove", methods=["POST"])
def api_remove():
    code = request.json.get("section_code", "").strip()
    config = load_config()
    if code not in config["courses"]:
        return jsonify({"ok": False, "error": f"Section {code} not in watch list."}), 400

    config["courses"].remove(code)
    save_config(config)
    return jsonify({"ok": True, "message": f"Removed {code}"})


@app.route("/api/config", methods=["POST"])
def api_config():
    data = request.json
    config = load_config()

    if "term" in data:
        config["term"] = data["term"]
    if "check_interval_seconds" in data:
        val = int(data["check_interval_seconds"])
        config["check_interval_seconds"] = max(10, val)
    if "sender_email" in data:
        config["email"]["sender_email"] = data["sender_email"]
    if "sender_password" in data and data["sender_password"]:
        config["email"]["sender_password"] = data["sender_password"]
    if "recipient_email" in data:
        config["email"]["recipient_email"] = data["recipient_email"]

    save_config(config)
    return jsonify({"ok": True, "message": "Config saved"})


@app.route("/api/monitor/start", methods=["POST"])
def api_monitor_start():
    global monitor_thread, monitor_running

    if monitor_running:
        return jsonify({"ok": False, "error": "Monitor already running"})

    config = load_config()
    if not config["courses"]:
        return jsonify({"ok": False, "error": "No sections to watch. Add some first."}), 400

    monitor_running = True
    add_log("Monitor started")
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    return jsonify({"ok": True, "message": "Monitor started"})


@app.route("/api/monitor/stop", methods=["POST"])
def api_monitor_stop():
    global monitor_running

    if not monitor_running:
        return jsonify({"ok": False, "error": "Monitor not running"})

    monitor_running = False
    add_log("Monitor stopped")
    return jsonify({"ok": True, "message": "Monitor stopped"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
