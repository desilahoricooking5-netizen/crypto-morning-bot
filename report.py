"""Roz subah crypto report aur BTC ke foran alerts (free, bina AI ke).

Modes:
  python report.py morning   -> subah ki poori report email karta hai
  python report.py alert     -> badi BTC khabar ya price move par alert email
  python report.py test      -> sirf ek test email (setup check karne ke liye)
"""
import html as htmllib
import json
import os
import re
import smtplib
import ssl
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

PKT = ZoneInfo("Asia/Karachi")

# Coins: naam -> Kraken pair. Naya coin add karna ho to yahan ek line badhayein.
COINS = {"BTC": "XBTUSD", "ETH": "ETHUSD", "SOL": "SOLUSD"}

FEEDS = [
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("Decrypt", "https://decrypt.co/feed"),
]

PRICE_MOVE_PCT = 2.0            # 1 ghante mein itna % hile to alert
PRICE_ALERT_COOLDOWN_HOURS = 3  # price alert ke baad itni der dobara nahi
NEWS_MAX_AGE_HOURS = 3          # sirf itni taaza khabar par alert

STATE_FILE = "state.json"
UA = {"User-Agent": "Mozilla/5.0 (crypto-morning-bot)"}

BTC_WORD = re.compile(r"\b(bitcoin|btc)\b", re.I)
BIG_WORDS = re.compile(
    r"\b(etfs?|sec|hack|hacked|hacker|exploit|ban|banned|fed|fomc|blackrock|"
    r"fidelity|halving|crash|crashes|plunge|plunges|plummets|surge|surges|"
    r"soars|rally|record|all-time|ath|liquidations?|lawsuit|approves?|"
    r"approval|reserve|tariffs?|bankruptcy|binance|coinbase|tether|"
    r"regulation|regulator|arrest|arrested|fraud|rate cut|rate hike|"
    r"inflation|cpi)\b",
    re.I,
)


# ---------- chhote helpers ----------
def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def money(x):
    return f"${x:,.2f}" if x >= 1 else f"${x:.4f}"


def pkt_now():
    return datetime.now(PKT).strftime("%d %b %Y, %I:%M %p")


def kraken_ohlc(pair, interval):
    """Candles: [time, open, high, low, close]. Aakhri candle abhi chal rahi hoti hai."""
    data = json.loads(get(f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"))
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    res = data["result"]
    key = [k for k in res if k != "last"][0]
    return [[float(x) for x in row[:5]] for row in res[key]]


def get_news():
    items = []
    for source, url in FEEDS:
        try:
            root = ET.fromstring(get(url))
            for it in root.iter("item"):
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                pub = it.findtext("pubDate")
                if not title or not link or not pub:
                    continue
                t = parsedate_to_datetime(pub)
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                items.append({"source": source, "title": title, "link": link, "time": t})
        except Exception as e:  # ek feed band ho to baqi chalti rahein
            print(f"Feed fail: {source}: {e}")
    items.sort(key=lambda x: x["time"], reverse=True)
    return items


def is_big_btc_news(title):
    return bool(BTC_WORD.search(title) and BIG_WORDS.search(title))


def send_email(subject, html_body, text_body):
    addr = os.environ["GMAIL_ADDRESS"].strip()
    pwd = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "").strip()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = addr
    msg["To"] = addr
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(addr, pwd)
        s.send_message(msg)
    print("Email bhej di gayi:", subject)


def news_html(items):
    if not items:
        return "<p>Abhi koi taaza khabar nahi mili.</p>"
    out = "<ul>"
    for n in items:
        out += (
            f'<li><a href="{htmllib.escape(n["link"])}">{htmllib.escape(n["title"])}</a> '
            f'<small>({n["source"]})</small></li>'
        )
    return out + "</ul>"


def news_text(items):
    return "\n".join(f"- {n['title']} ({n['source']})\n  {n['link']}" for n in items) or "Koi khabar nahi."


# ---------- subah ki report ----------
def morning():
    rows_html, rows_text = "", ""
    for name, pair in COINS.items():
        try:
            c = kraken_ohlc(pair, 1440)
            today, yest = c[-1], c[-2]
            change = (yest[4] - yest[1]) / yest[1] * 100
            now_price = today[4]
            arrow = "&#9650;" if change >= 0 else "&#9660;"
            color = "#0a8f3c" if change >= 0 else "#d32f2f"
            rows_html += (
                f"<tr><td><b>{name}</b></td>"
                f"<td>{money(now_price)}</td>"
                f"<td>{money(today[1])}</td>"
                f"<td>{money(yest[1])}</td>"
                f"<td>{money(yest[4])}</td>"
                f'<td style="color:{color}">{arrow} {change:+.2f}%</td></tr>'
            )
            rows_text += (
                f"{name}: abhi {money(now_price)} | aaj ki open {money(today[1])} | "
                f"kal open {money(yest[1])} -> close {money(yest[4])} ({change:+.2f}%)\n"
            )
        except Exception as e:
            rows_html += f"<tr><td><b>{name}</b></td><td colspan='5'>Data nahi mila ({htmllib.escape(str(e))})</td></tr>"
            rows_text += f"{name}: data nahi mila ({e})\n"

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    news = [n for n in get_news() if n["time"] >= cutoff][:10]

    html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:640px">
<h2>Subah ki Crypto Report</h2>
<p><small>{pkt_now()} (Pakistan time)</small></p>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
<tr style="background:#f0f0f0"><th>Coin</th><th>Abhi ki price</th><th>Aaj ki open</th>
<th>Kal ki open</th><th>Kal ki close</th><th>Kal ka change</th></tr>
{rows_html}
</table>
<p><small>Candle UTC ke hisaab se hoti hai: Pakistan mein subah 5 baje se agle din subah 5 baje tak.</small></p>
<h3>Taaza khabrein (pichle 24 ghante)</h3>
{news_html(news)}
<p><small>Ye maloomat sirf jaankari ke liye hai, mashwara nahi.</small></p>
</div>"""
    text_body = (
        f"Subah ki Crypto Report ({pkt_now()} PKT)\n\n{rows_text}\n"
        f"Taaza khabrein:\n{news_text(news)}\n"
    )
    send_email("Subah ki Crypto Report: BTC, ETH, SOL", html_body, text_body)


# ---------- foran alert ----------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)


def alert():
    state = load_state()
    first_run = "seen" not in state
    seen = set(state.get("seen", []))
    now = datetime.now(timezone.utc)
    reasons_html, reasons_text = "", ""
    subject_bits = []

    # 1) Badi BTC khabar
    news = get_news()
    fresh_limit = now - timedelta(hours=NEWS_MAX_AGE_HOURS)
    big = [
        n for n in news
        if n["link"] not in seen and n["time"] >= fresh_limit and is_big_btc_news(n["title"])
    ]
    if big and not first_run:
        subject_bits.append("badi khabar")
        reasons_html += "<h3>Badi BTC khabar</h3>" + news_html(big)
        reasons_text += "Badi BTC khabar:\n" + news_text(big) + "\n\n"
    seen.update(n["link"] for n in news)
    state["seen"] = list(seen)[-600:]

    # 2) BTC price achanak hile
    try:
        c = kraken_ohlc(COINS["BTC"], 15)
        last, ref = c[-1][4], c[-5][4]  # abhi vs taqreeban 1 ghanta pehle
        move = (last - ref) / ref * 100
        last_alert = state.get("last_price_alert")
        cooled = True
        if last_alert:
            cooled = now - datetime.fromisoformat(last_alert) >= timedelta(hours=PRICE_ALERT_COOLDOWN_HOURS)
        if abs(move) >= PRICE_MOVE_PCT and cooled:
            word = "upar" if move > 0 else "neeche"
            subject_bits.append(f"price {move:+.1f}%")
            reasons_html += (
                f"<h3>BTC ki price tezi se {word} gayi</h3>"
                f"<p>Taqreeban 1 ghante mein {move:+.2f}%: {money(ref)} se {money(last)}.</p>"
            )
            reasons_text += f"BTC taqreeban 1 ghante mein {move:+.2f}%: {money(ref)} -> {money(last)}\n"
            state["last_price_alert"] = now.isoformat()
    except Exception as e:
        print("Price check fail:", e)

    save_state(state)

    if not subject_bits:
        print("Koi alert nahi.")
        return
    html_body = (
        f'<div style="font-family:Arial,sans-serif;max-width:640px"><h2>BTC Alert</h2>'
        f"<p><small>{pkt_now()} (Pakistan time)</small></p>{reasons_html}"
        f"<p><small>Ye maloomat sirf jaankari ke liye hai, mashwara nahi.</small></p></div>"
    )
    send_email("BTC Alert: " + ", ".join(subject_bits), html_body, f"BTC Alert ({pkt_now()} PKT)\n\n{reasons_text}")


def test():
    send_email(
        "Test email: Crypto bot theek chal raha hai",
        "<p>Mubarak ho! Aapka crypto bot email bhej raha hai.</p>",
        "Mubarak ho! Aapka crypto bot email bhej raha hai.",
    )


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    {"morning": morning, "alert": alert, "test": test}[mode]()
