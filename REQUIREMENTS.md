# Software Requirements Specification

**Project:** Course Sniper
**Version:** 1.0
**Date:** 2026-06-28
**Author:** Ray Li

---

## 1. Introduction

### 1.1 Purpose

This document specifies the software requirements for Course Sniper, a CLI tool that monitors UCI course enrollment and notifies users when open spots become available. It is intended for use by developers contributing to the project and serves as a reference for current and future functionality.

### 1.2 Scope

Course Sniper is a Python command-line application that polls UCI's Schedule of Classes data and sends email alerts when a watched course section has an open enrollment spot. The system does not handle enrollment itself — it only monitors and notifies.

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

Course Sniper is a standalone tool. It depends on two external data sources (Anteater API and UCI WebSOC) and one external service (an SMTP email provider). It has no database, no web interface, and no user accounts — configuration is stored in a local JSON file.

### 2.2 User Characteristics

The target user is a UCI student with basic command-line familiarity who wants to be notified when a full class has an opening. No programming knowledge is required beyond running `python` commands.

### 2.3 Constraints

- Relies on third-party API availability (Anteater API, UCI WebSOC).
- Anteater API caches WebSOC data; real-time accuracy depends on their refresh interval.
- Email delivery depends on the user's SMTP provider.
- Must not send excessive requests that would overload UCI systems.

### 2.4 Assumptions

- The user has Python 3.10+ installed.
- The user has a Gmail account (or other SMTP-compatible email) with App Passwords enabled.
- UCI continues to provide public access to WebSOC and does not block automated queries at reasonable intervals.

---

## 3. Functional Requirements

### FR-1: Add Section to Watch List

- **Description**: The user can add a 5-digit UCI section code to their watch list.
- **Input**: Section code (string, 5 digits).
- **Behavior**: Appends the code to the `courses` array in `config.json`. Rejects duplicates.
- **Output**: Confirmation message.

### FR-2: Remove Section from Watch List

- **Description**: The user can remove a section code from their watch list.
- **Input**: Section code.
- **Behavior**: Removes the code from `config.json`. Reports if not found.
- **Output**: Confirmation message.

### FR-3: List Watched Sections

- **Description**: The user can view all watched sections with their current enrollment status.
- **Input**: None.
- **Behavior**: For each watched section, queries the API and displays course name, enrollment count, capacity, and open/full status.
- **Output**: Formatted list with status indicators.

### FR-4: Quick-Check a Section

- **Description**: The user can check the current status of any section code without adding it to the watch list.
- **Input**: Section code.
- **Behavior**: Queries the API and displays detailed section info.
- **Output**: Course name, section type, status, enrollment, waitlist, and instructor.

### FR-5: Configure Settings

- **Description**: The user can configure the term, check interval, and email credentials via an interactive prompt.
- **Input**: User responses to prompts (term, interval, sender email, app password, recipient email).
- **Behavior**: Updates `config.json` with new values. Existing values are shown as defaults and preserved if the user presses Enter.
- **Output**: Confirmation message.

### FR-6: Monitor Sections

- **Description**: The system continuously polls watched sections and sends email notifications when a spot opens.
- **Input**: None (reads from `config.json`).
- **Behavior**:
  - Loops every `check_interval_seconds` (default: 30).
  - For each watched section, checks if status is OPEN or enrolled < capacity.
  - On first detection of an open spot, sends one email notification.
  - If the spot fills and re-opens later, sends another notification.
  - Prints timestamped status to stdout.
- **Output**: Console log + email notifications.
- **Preconditions**: At least one section in watch list; email configured.

### FR-7: Email Notification

- **Description**: The system sends an email containing course details and a link to WebReg.
- **Input**: Section info dict, email config.
- **Behavior**: Constructs a plain-text email with course name, section code, enrollment numbers, instructor, and WebReg URL. Sends via SMTP with TLS.
- **Output**: Email delivered to recipient; success/failure logged to console.

### FR-8: API Fallback

- **Description**: If the Anteater API is unavailable or returns an error, the system falls back to scraping UCI WebSOC directly.
- **Input**: Same section code and term.
- **Behavior**: POSTs to WebSOC with form data, parses the HTML response.
- **Output**: Same section info dict as the primary API path.

---

## 4. Non-Functional Requirements

### NFR-1: Performance

- Each polling cycle should complete within 10 seconds for up to 20 watched sections.
- API requests use a 10-second timeout.

### NFR-2: Reliability

- The monitor loop must not crash on transient API errors — it logs warnings and continues.
- Failed email sends are logged but do not stop monitoring.

### NFR-3: Usability

- All CLI commands are documented in `--help` output (module docstring).
- Error messages are descriptive (e.g., "Email not configured. Run 'python main.py config' first.").

### NFR-4: Rate Limiting

- Default check interval is 30 seconds to avoid excessive load on external services.
- Configurable by the user but should not be set below 10 seconds.

### NFR-5: Security

- Email credentials are stored in a local `config.json` file. The file should not be committed to version control (covered by `.gitignore`).

---

## 5. Future Enhancements

These are not in scope for v1.0 but are documented for future reference:

- **Multi-user support**: Allow multiple recipient emails per section.
- **SMS notifications**: Integrate Twilio or similar for text alerts.
- **Web dashboard**: A simple web UI to manage watch lists and view status.
- **Waitlist monitoring**: Notify when waitlist count drops, not just when status is OPEN.
- **Auto-enrollment**: Integrate with WebReg to automatically enroll (would require authentication — significant complexity and policy considerations).
- **Docker deployment**: Package as a container for always-on monitoring.
- **Rate limit backoff**: Exponential backoff if the API returns 429 or 5xx errors.
