#!/usr/bin/env python3
"""
Course Sniper — UCI class enrollment monitor.

Watches UCI course sections and emails you when a spot opens up.

Usage:
    python main.py add <section_code>       Add a section to watch
    python main.py remove <section_code>    Remove a section from watch list
    python main.py list                     Show all watched sections
    python main.py check <section_code>     Quick-check a section's status
    python main.py config                   Set up email and term
    python main.py run                      Start monitoring

Section codes are the 5-digit codes from UCI's Schedule of Classes (WebSOC).
Find them at: https://www.reg.uci.edu/perl/WebSoc
"""

import sys
import json
import time
from datetime import datetime
from pathlib import Path

from checker import check_section, has_open_spot
from notifier import send_email

CONFIG_PATH = Path(__file__).parent / "config.json"


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


def cmd_add(section_code: str):
    config = load_config()
    if section_code in config["courses"]:
        print(f"Section {section_code} is already in your watch list.")
        return
    config["courses"].append(section_code)
    save_config(config)
    print(f"Added section {section_code} to watch list.")


def cmd_remove(section_code: str):
    config = load_config()
    if section_code not in config["courses"]:
        print(f"Section {section_code} is not in your watch list.")
        return
    config["courses"].remove(section_code)
    save_config(config)
    print(f"Removed section {section_code} from watch list.")


def cmd_list():
    config = load_config()
    if not config["courses"]:
        print("No sections in your watch list. Use 'python main.py add <code>' to add one.")
        return
    print(f"Term: {config['term']}")
    print(f"Watching {len(config['courses'])} section(s):\n")
    for code in config["courses"]:
        info = check_section(config["term"], code)
        if info:
            status_icon = "🟢" if has_open_spot(info) else "🔴"
            print(f"  {status_icon} {code} — {info['dept']} {info['course_number']} "
                  f"({info['course_title']}) — {info['enrolled']}/{info['max_capacity']} — {info['status']}")
        else:
            print(f"  ⚪ {code} — Could not fetch info")


def cmd_check(section_code: str):
    config = load_config()
    term = config["term"]
    print(f"Checking section {section_code} for {term}...\n")
    info = check_section(term, section_code)
    if info:
        status_icon = "OPEN" if has_open_spot(info) else "FULL"
        print(f"  Course:      {info['dept']} {info['course_number']} - {info['course_title']}")
        print(f"  Section:     {section_code} ({info['section_type']})")
        print(f"  Status:      {status_icon} ({info['status']})")
        print(f"  Enrolled:    {info['enrolled']} / {info['max_capacity']}")
        print(f"  Waitlist:    {info['waitlist'] or 'N/A'}")
        print(f"  Instructor:  {', '.join(info['instructors']) if info['instructors'] else 'N/A'}")
    else:
        print(f"  Could not find section {section_code}. Check the code and term.")


def cmd_config():
    config = load_config()
    print("Configure Course Sniper\n")

    term = input(f"Term [{config['term']}]: ").strip()
    if term:
        config["term"] = term

    interval = input(f"Check interval in seconds [{config['check_interval_seconds']}]: ").strip()
    if interval:
        config["check_interval_seconds"] = int(interval)

    print("\nEmail settings (for Gmail, use an App Password — not your regular password):")
    email_cfg = config["email"]

    sender = input(f"Sender email [{email_cfg['sender_email']}]: ").strip()
    if sender:
        email_cfg["sender_email"] = sender

    password = input(f"App password [{'****' if email_cfg['sender_password'] else 'not set'}]: ").strip()
    if password:
        email_cfg["sender_password"] = password

    recipient = input(f"Recipient email [{email_cfg['recipient_email']}]: ").strip()
    if recipient:
        email_cfg["recipient_email"] = recipient

    save_config(config)
    print("\nConfig saved!")


def cmd_run():
    config = load_config()

    if not config["courses"]:
        print("No sections to watch. Use 'python main.py add <code>' first.")
        return

    email_cfg = config["email"]
    if not email_cfg["sender_email"] or not email_cfg["sender_password"]:
        print("Email not configured. Run 'python main.py config' first.")
        return

    term = config["term"]
    interval = config["check_interval_seconds"]
    notified = set()  # Track which sections we've already notified about

    print(f"🎯 Course Sniper running — watching {len(config['courses'])} section(s)")
    print(f"   Term: {term}")
    print(f"   Checking every {interval} seconds")
    print(f"   Notifications → {email_cfg['recipient_email']}")
    print(f"   Press Ctrl+C to stop\n")

    try:
        while True:
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] Checking {len(config['courses'])} section(s)...")
            for code in config["courses"]:
                info = check_section(term, code)
                if info is None:
                    print(f"[WARN] Could not fetch section {code}")
                    continue

                label = f"{info['dept']} {info['course_number']} ({code})"

                if has_open_spot(info):
                    if code not in notified:
                        print(f"[OPEN] {label} — {info['enrolled']}/{info['max_capacity']} — SENDING EMAIL")
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
                    else:
                        print(f"[OPEN] {label} — already notified")
                else:
                    if code in notified:
                        # Spot filled again, reset so we can notify on next opening
                        notified.discard(code)
                    print(f"[FULL] {label} — {info['enrolled']}/{info['max_capacity']}")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nStopped. Zot zot! 🐜")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "add" and len(sys.argv) == 3:
        cmd_add(sys.argv[2])
    elif command == "remove" and len(sys.argv) == 3:
        cmd_remove(sys.argv[2])
    elif command == "list":
        cmd_list()
    elif command == "check" and len(sys.argv) == 3:
        cmd_check(sys.argv[2])
    elif command == "config":
        cmd_config()
    elif command == "run":
        cmd_run()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
