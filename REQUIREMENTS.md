# Software Requirements Specification

**Project:** Course Sniper
**Version:** 2.1
**Date:** 2026-06-28
**Author:** Ray Li

---

## 1. Introduction

### 1.1 Purpose

This document specifies the software requirements for Course Sniper, a public web application that monitors UCI course enrollment and emails users when spots become available.

### 1.2 Scope

Course Sniper is a single-page web app where anyone enters their email and a UCI section code. The server monitors all watched sections and sends email notifications when spots open. No accounts, no login, no passwords.

### 1.3 Definitions and Acronyms

- **WebSOC**: Web Schedule of Classes — UCI's official course listing system.
- **WebReg**: UCI's online enrollment portal.
- **Section Code**: A unique 5-digit identifier for a course section in WebSOC.
- **Anteater API**: A REST API maintained by ICSSC for UCI course data.
- **SMTP**: Simple Mail Transfer Protocol.

### 1.4 References

- UCI WebSOC: https://www.reg.uci.edu/perl/WebSoc
- Anteater API: https://anteaterapi.com/v2/rest/websoc
- IEEE 830-1998 (SRS standard)

---

## 2. Overall Description

### 2.1 Product Perspective

A publicly hosted web app. Uses SQLite for storing watch requests. A single background thread polls the Anteater API for all watched sections (deduplicated) and sends emails via a server-configured Gmail account. No user accounts or authentication.

### 2.2 User Characteristics

Any UCI student. No technical knowledge required.

### 2.3 Constraints

- Relies on Anteater API and UCI WebSOC availability.
- Email delivery requires server-side SMTP credentials.
- Check interval fixed at 30 seconds.
- Free hosting (Render) spins down after inactivity.

---

## 3. Functional Requirements

### FR-1: Set Email

- **Input**: Email address.
- **Behavior**: Stores in browser localStorage. Used for all subsequent actions. User enters it once per device.
- **Output**: Confirmation toast. Watch list loads automatically.

### FR-2: Watch a Section

- **Input**: 5-digit section code (email from FR-1).
- **Behavior**: Validates code. Verifies section exists via API. Saves to database (rejects duplicates). Auto-starts the background monitor.
- **Output**: Confirmation message with course name and current enrollment status.

### FR-3: Quick-Check a Section

- **Input**: 5-digit section code.
- **Behavior**: Queries API, returns current status without saving anything.
- **Output**: Course name, OPEN/FULL status, enrollment count, instructor.

### FR-4: View My Watches

- **Input**: Email from FR-1.
- **Behavior**: Looks up all watches for that email. Queries API for current status of each. Auto-refreshes every 30 seconds.
- **Output**: List with green/red status dots, enrollment counts, remove buttons.

### FR-5: Remove a Watch

- **Input**: Email + section code.
- **Behavior**: Deletes the watch record.
- **Output**: Confirmation message.

### FR-6: Background Monitor

- **Behavior**:
  - Collects all un-notified watches from database.
  - Groups by section code (deduplicated API calls).
  - Checks each section every 30 seconds.
  - On open spot: emails all users watching that section, marks as notified.
  - When a section fills back up: resets notified flag so users get re-notified if it opens again.
- **Output**: Emails sent to users; log entries.

### FR-7: Email Notification

- **Behavior**: Sends plain-text email with course name, section code, enrollment count, instructor, and WebReg link.
- **Sender**: Server-configured Gmail via SMTP/TLS.

### FR-8: API Fallback

- **Behavior**: If Anteater API fails, scrapes WebSOC directly.

---

## 4. Non-Functional Requirements

### NFR-1: Performance

- Polling cycle completes within 15 seconds for up to 100 unique sections.
- API requests timeout after 10 seconds.

### NFR-2: Reliability

- Monitor survives transient API errors.
- Failed emails are logged but don't stop monitoring.

### NFR-3: Scalability

- Deduplicated API calls: 50 users watching the same section = 1 API call.

### NFR-4: Security

- SMTP credentials stored as environment variables, never in code.
- No user passwords stored (no accounts).
- Database file is git-ignored.

### NFR-5: Usability

- Single page with four cards: Email, Add Section, Watch List, Monitor.
- Email entered once per device (stored in localStorage).
- Works on mobile.

---

## 5. Change Log

| Version | Date       | Changes |
|---------|------------|---------|
| 1.0     | 2026-06-28 | CLI-only, single-user |
| 1.1     | 2026-06-28 | Added web UI, browser notifications, sound alerts |
| 2.0     | 2026-06-28 | Multi-user with accounts, SQLite, deployment config |
| 2.1     | 2026-06-28 | Simplified: removed accounts/login, single email field, old-style UI with 4 cards |

---

## 6. Future Enhancements

- SMS notifications via Twilio.
- Waitlist count monitoring.
- Admin dashboard for system health.
- PostgreSQL for production scale.
