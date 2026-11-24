"""Email Resend ke zariye bhejta hai (Gmail App Password ki zaroorat nahi)."""
import json
import os
import sys
import urllib.error
import urllib.request

import report


def send_email(subject, html_body, text_body):
    key = os.environ["RESEND_API_KEY"].strip()
    to = os.environ["TO_EMAIL"].strip()
    payload = {
        "from": "Crypto Bot <onboarding@resend.dev>",
        "to": [to],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
            "User-Agent": "crypto-morning-bot/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("Email bhej di gayi:", subject, r.status)
    except urllib.error.HTTPError as e:
        print("Resend error", e.code, e.read().decode("utf-8", "replace"))
        raise


report.send_email = send_email

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    {"morning": report.morning, "alert": report.alert, "test": report.test}[mode]()
