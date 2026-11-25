"""Email Resend ke zariye bhejta hai (Gmail App Password ki zaroorat nahi)."""
import json
import os
import sys
import urllib.error
import urllib.request

import report
import report_pretty

ATTACHMENT = None  # subah ki report ke liye audio (base64 MP3)

BANNER = (
    '<div style="background:#312e81;color:#e0e7ff;border-radius:10px;padding:10px 14px;'
    'font-size:13px;margin:0 0 12px">&#128266; Audio report attach hai: '
    'subah-ki-report.mp3 kholein aur play dabayein.</div>'
)


def send_email(subject, html_body, text_body):
    key = os.environ["RESEND_API_KEY"].strip()
    to = os.environ["TO_EMAIL"].strip()
    if ATTACHMENT:
        html_body = html_body.replace("EK NAZAR MEIN</div>", "EK NAZAR MEIN</div>" + BANNER, 1)
    payload = {
        "from": "Crypto Bot <onboarding@resend.dev>",
        "to": [to],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }
    if ATTACHMENT:
        payload["attachments"] = [{"filename": "subah-ki-report.mp3", "content": ATTACHMENT}]
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
    if mode == "morning":
        try:
            import audio

            ATTACHMENT = audio.build_mp3_b64()
            print("Audio ban gayi.")
        except Exception as e:  # audio fail ho to bhi report email ho jaye
            print("Audio nahi ban saki, bina audio ke bhej rahe hain:", e)
    {"morning": report_pretty.morning, "alert": report.alert, "test": report.test}[mode]()
