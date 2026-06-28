# Software Requirements Specification

**Project:** Course Sniper
**Version:** 1.1
**Date:** 2026-06-28
**Author:** Ray Li

---

## 1. Introduction

### 1.1 Purpose

This document specifies the software requirements for Course Sniper, a web-based and CLI tool that monitors UCI course enrollment and notifies users when open spots become available. It is intended for use by developers contributing to the project and serves as a reference for current and future functionality.

### 1.2 Scope

Course Sniper is a Python application with a Flask web UI and a CLI interface. It polls UCI's Schedule of Classes data and alerts users via browser notifications, sound alerts, and optionally email when a watched course section has an open enrollment spot. The system does not handle enrollment itself — it only monitors and notifies.

### 1.3 Definitions and Acronyms

- **WebSOC**: Web Schedule of Classes — UCI's official course listing system.
- **WebReg**: UCI's online enrollment portal where students add/drop classes.
- **Section Code**: A unique 5-digit identifier for a specific course section in WebSOC.
- **Anteater API**: A third-party REST API maintained by ICSSC that provides structured access to WebSOC data.
- **SMTP**: Simple Mail Transfer Protocol — used to send email notifications.
- **App Password**: A Google-generated password for third-party app access when 2FA is enabled.

### 1.4 References

- UCI WebSOC: https://www.reg.uci.edu/perl/WebSoc
- Anteater API Docs: https://docs.icssc.club/docs/developer/anteaterapi
- Anteater API Base URL: https://anteaterapi.com/v2/rest/websoc
- IEEE 830-1998 (SRS standard)

---

## 2. Overall Description

### 2.1 Product Perspective

Course Sniper is a standalone tool with two interfaces: a Flask web dashboard (primary) and a CLI (secondary). It depends on two external data sources (Anteater API and UCI WebSOC). Email notifications optionally depend on an SMTP provider. It has no database and no user accounts — configuration is stored in a local JSON file.

### 2.2 User Characteristics

The target user is a UCI student who wants to be notified when a full class has an opening. No programming knowledge is required — the web UI is the primary interface. The CLI is available for users who prefer it.

### 2.3 Constraints

- Relies on third-party API availability (Anteater API, UCI WebSOC).
- Anteater API caches WebSOC data; real-time accuracy depends on their refresh interval.
- Browser notifications require the user to grant permission and keep the tab open.
- Email delivery depends on the user's SMTP provider (optional).
- Must not send excessive requests that would overload UCI systems.
- Check interval is fixed at 30 seconds and not user-configurable.

### 2.4 Assumptions

- The user has Python 3.10+ installed.
- The user is using a modern browser that supports the Notifications API and Web Audio API.
- UCI continues to provide public access to WebSOC and does not block automated queries at reasonable intervals.

---

## 3. Functional Requirements

### FR-1: Add Section to Watch List

- **Description**: The user can add a 5-digit UCI section code to their watch list.
- **Input**: Section code (string, 5 digits).
- **Behavior**: Validates the code is exactly 5 digits. Appends to the `courses` array in `config.json`. Rejects duplicates.
- **Output**: Confirmation message (toast notification in web UI).

### FR-2: Remove Section from Watch List

- **Description**: The user can remove a section code from their watch list.
- **Input**: Section code.
- **Behavior**: Removes the code from `config.json`. Reports if not found.
- **Output**: Confirmation message.

### FR-3: List Watched Sections

- **Description**: The user can view all watched sections with their current enrollment status.
- **Input**: None.
- **Behavior**: For each watched section, queries the API and displays course name, enrollment count, capacity, and open/full status.
- **Output**: Formatted list with green/red status indicators (web UI) or emoji indicators (CLI).

### FR-4: Quick-Check a Section

- **Description**: The user can check the current status of any section code without adding it to the watch list.
- **Input**: Section code.
- **Behavior**: Queries the API and displays detailed section info inline.
- **Output**: Course name, section type, status, enrollment, waitlist, and instructor.

### FR-5: Configure Settings

- **Description**: The user can configure the term and optionally email credentials.
- **Input**: Term string (web UI or CLI), email address and app password (optional, web UI collapsible section or CLI prompt).
- **Behavior**: Updates `config.json`. Check interval is fixed at 30 seconds and not exposed to the user.
- **Output**: Confirmation message.

### FR-6: Monitor Sections

- **Description**: The system continuously polls watched sections and sends notifications when a spot opens.
- **Input**: None (reads from `config.json`).
- **Behavior**:
  - Runs as a background thread (web UI) or foreground loop (CLI).
  - Polls every 30 seconds (fixed).
  - For each watched section, checks if status is OPEN or enrolled < capacity.
  - On first detection of an open spot, queues a browser alert and optionally sends email.
  - If the spot fills and re-opens later, notifies again.
  - Logs timestamped status entries viewable in the web UI log box or CLI stdout.
- **Output**: Browser notifications + sound alert (web UI), console log, and optionally email.
- **Preconditions**: At least one section in watch list.

### FR-7: Browser Notifications

- **Description**: When the monitor detects an open spot, the system shows a browser push notification with course details and plays a sound alert.
- **Input**: Alert data from the monitor (section code, course name, enrollment).
- **Behavior**: The frontend polls `/api/alerts` every 5 seconds while the monitor is running. New alerts trigger a browser Notification (requires user permission) and a synthesized tone sequence via Web Audio API.
- **Output**: Browser notification popup with course info; audible alert tone.
- **Preconditions**: User has granted notification permission; tab is open.

### FR-8: Email Notification (Optional)

- **Description**: The system can optionally send an email containing course details and a link to WebReg.
- **Input**: Section info dict, email config.
- **Behavior**: Constructs a plain-text email with course name, section code, enrollment numbers, instructor, and WebReg URL. Sends via SMTP with TLS. Uses a single email address for both sender and recipient.
- **Output**: Email delivered; success/failure logged.
- **Preconditions**: User has configured Gmail address and App Password.

### FR-9: API Fallback

- **Description**: If the Anteater API is unavailable or returns an error, the system falls back to scraping UCI WebSOC directly.
- **Input**: Same section code and term.
- **Behavior**: POSTs to WebSOC with form data, parses the HTML response.
- **Output**: Same section info dict as the primary API path.

---

## 4. Non-Functional Requirements

### NFR-1: Performance

- Each polling cycle should complete within 10 seconds for up to 20 watched sections.
- API requests use a 10-second timeout.
- Frontend alert polling runs every 5 seconds for low-latency notifications.

### NFR-2: Reliability

- The monitor loop must not crash on transient API errors — it logs warnings and continues.
- Failed email sends are logged but do not stop monitoring.
- Browser notifications degrade gracefully if permission is denied (sound alert still plays).

### NFR-3: Usability

- The web UI works with zero configuration — just add section codes and start the monitor.
- Help text and field hints guide users through each section of the UI.
- Email setup is optional and collapsed by default to reduce friction.
- All CLI commands are documented in the module docstring.

### NFR-4: Rate Limiting

- Check interval is fixed at 30 seconds to avoid excessive load on external services.
- The interval is not user-configurable to prevent abuse.

### NFR-5: Security

- Email credentials are stored in a local `config.json` file.
- `config.json` is excluded from version control via `.gitignore`.
- App Password is masked in the UI after being set.

---

## 5. Change Log

| Version | Date       | Changes                                                                 |
|---------|------------|-------------------------------------------------------------------------|
| 1.0     | 2026-06-28 | Initial release: CLI-only, email notifications, Anteater API + WebSOC fallback |
| 1.1     | 2026-06-28 | Added Flask web UI, browser notifications, sound alerts, made email optional, removed user-configurable interval |

---

## 6. Future Enhancements

These are not in scope for v1.1 but are documented for future reference:

- **Multi-user support**: Allow multiple recipient emails per section.
- **SMS notifications**: Integrate Twilio or similar for text alerts.
- **Waitlist monitoring**: Notify when waitlist count drops, not just when status is OPEN.
- **Auto-enrollment**: Integrate with WebReg to automatically enroll (would require authentication — significant complexity and policy considerations).
- **Docker deployment**: Package as a container for always-on monitoring.
- **Rate limit backoff**: Exponential backoff if the API returns 429 or 5xx errors.
- **Mobile push notifications**: PWA support or integration with a push service for mobile alerts.
