"""
Email notifier for course availability alerts.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(smtp_server: str, smtp_port: int, sender_email: str,
               sender_password: str, recipient_email: str,
               section_info: dict) -> bool:
    """
    Send an email notification that a course spot opened up.
    Returns True on success, False on failure.
    """
    subject = (
        f"🎯 SPOT OPEN: {section_info['dept']} {section_info['course_number']} "
        f"- {section_info['course_title']}"
    )

    body = f"""A spot just opened up in a class you're watching!

Course: {section_info['dept']} {section_info['course_number']} - {section_info['course_title']}
Section Code: {section_info['section_code']}
Type: {section_info['section_type']}
Status: {section_info['status']}
Enrolled: {section_info['enrolled']} / {section_info['max_capacity']}
Waitlist: {section_info['waitlist']}
Instructor(s): {', '.join(section_info['instructors'])}

Go enroll NOW → https://www.reg.uci.edu/cgi-bin/webreg2/Main

— Course Sniper 🎯
"""

    msg = MIMEMultipart()
    msg["From"] = f"Course Sniper <{sender_email}>"
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"[EMAIL] Notification sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False
