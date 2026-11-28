"""Email Resend ke zariye bhejta hai (Gmail App Password ki zaroorat nahi)."""
import html as htmllib
import json
import os
import sys
import urllib.error
import urllib.request

import report
import report_pretty

ATTACHMENT = None  # subah ki report ke liye audio (base64 MP3)
CHART_B64 = None   # BTC chart ki PNG (base64)
CHART_TEXT = None  # BTC chart ka Roman Urdu tajziya

BANNER = (
    '<div style="background:#312e81;color:#e0e7ff;border-radius:10px;padding:10px 14px;'
    'font-size:13px;margin:0 0 12px">&#128266; Khabron ki audio attach hai: '
    'subah-ki-khabrein.mp3 kholein aur play dabayein.</div>'
)


def chart_block_html(inline=True):
    body = htmllib.escape(CHART_TEXT or "").replace("\n", "<br>")
    if inline:
        img = ('<img src="cid:btc-chart" alt="BTC chart" width="100%" '
               'style="width:100%;border-radius:10px;display:block">')
    else:
        img = ('<div style="color:#94a3b8;font-size:13px">Chart attachment '
               '(btc-chart.png) mein hai.</div>')
    return (
        '<table width="100%" cellpadding="0" cellspacing="0" bgcolor="#1e293b" '
        'style="background:#1e293b;border-radius:14px;margin-bottom:18px"><tr>'
        '<td style="padding:18px 20px">'
        '<div style="font-size:12px;letter-spacing:2px;color:#f7931a;font-weight:bold;'
        'margin-bottom:10px">BTC CHART AUR TAJZIYA</div>'
        + img +
        '<div style="color:#f1f5f9;font-size:14px;line-height:1.6;margin-top:12px">'
        + body + '</div></td></tr></table>'
    )


def insert_chart(html_body, inline=True):
    """Chart ka card pehle coin card se pehle lagata hai."""
    i = html_body.find("border-left:6px solid")
    if i == -1:
        return html_body
    j = html_body.rfind("<table", 0, i)
    if j == -1:
        return html_body
    return html_body[:j] + chart_block_html(inline) + html_body[j:]


def _post(key, payload):
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
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status


def send_email(subject, html_body, text_body):
    key = os.environ["RESEND_API_KEY"].strip()
    to = os.environ["TO_EMAIL"].strip()
    if ATTACHMENT:
        html_body = html_body.replace("EK NAZAR MEIN</div>", "EK NAZAR MEIN</div>" + BANNER, 1)

    def build(inline):
        body = html_body
        text = text_body
        attachments = []
        if ATTACHMENT:
            attachments.append({"filename": "subah-ki-khabrein.mp3", "content": ATTACHMENT})
        if CHART_B64:
            body = insert_chart(body, inline)
            text = text + "\nBTC tajziya:\n" + (CHART_TEXT or "") + "\n"
            att = {"filename": "btc-chart.png", "content": CHART_B64}
            if inline:
                att["content_id"] = "btc-chart"
            attachments.append(att)
        payload = {
            "from": "Crypto Bot <onboarding@resend.dev>",
            "to": [to],
            "subject": subject,
            "html": body,
            "text": text,
        }
        if attachments:
            payload["attachments"] = attachments
        return payload

    try:
        status = _post(key, build(True))
        print("Email bhej di gayi:", subject, status)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        print("Resend error", e.code, detail)
        if CHART_B64 and e.code in (400, 422):
            # inline image support na ho to chart ko sirf attachment ki tarah bhejein
            status = _post(key, build(False))
            print("Email (chart attachment ke saath) bhej di gayi:", subject, status)
        else:
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
        try:
            import base64

            import btc_chart

            CHART_TEXT = btc_chart.build_btc_report("btc-chart.png")
            with open("btc-chart.png", "rb") as f:
                CHART_B64 = base64.b64encode(f.read()).decode("ascii")
            print("BTC chart ban gayi.")
        except Exception as e:  # chart fail ho to bhi report email ho jaye
            print("BTC chart nahi ban saki, bina chart ke bhej rahe hain:", e)
    {"morning": report_pretty.morning, "alert": report.alert, "test": report.test}[mode]()
