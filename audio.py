"""Subah ki khabron ka Hindi audio (MP3). gTTS + deep-translator (dono free, bina key ke)."""
import base64
import html as H
import io
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import report
import macro

ORDINALS = ["पहली", "दूसरी", "तीसरी", "चौथी", "पाँचवीं", "छठी", "सातवीं", "आठवीं"]
MAX_NEWS = 8
OTHER_COINS = re.compile(r"\b(ethereum|ether|eth|solana|sol)\b", re.I)
TAG = re.compile(r"<[^>]+>")
TAIL = re.compile(r"\s*The post .*? appeared first on .*$", re.I | re.S)
MAX_SUMMARY = 250  # translator ki free limit bachane ke liye


def clean_summary(raw, title):
    """Feed ke description se chhota saaf khulasa. Kuch kaam ka na ho to khali."""
    if not raw:
        return ""
    t = H.unescape(TAG.sub(" ", raw))
    t = TAIL.sub("", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) < 40 or t.lower().startswith(title.lower()[:30]):
        return ""
    if len(t) > MAX_SUMMARY:
        cut = t[:MAX_SUMMARY]
        k = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
        t = cut[: k + 1] if k > 80 else cut.rsplit(" ", 1)[0]
    return t


def fetch_items():
    items = []
    for source, url in report.FEEDS:
        try:
            root = ET.fromstring(report.get(url))
            for it in root.iter("item"):
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                pub = it.findtext("pubDate")
                if not title or not link or not pub:
                    continue
                t = parsedate_to_datetime(pub)
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                summary = clean_summary(it.findtext("description"), title)
                items.append({"source": source, "title": title, "link": link, "time": t, "summary": summary})
        except Exception as e:
            print("Audio feed fail:", source, e)
    return items


def pick_news():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    items = fetch_items() or [dict(n, summary="") for n in report.get_news()]
    items = [n for n in items if n["time"] >= cutoff]

    def score(n):
        t = n["title"]
        if report.is_big_btc_news(t):
            return 3
        if report.BTC_WORD.search(t):
            return 2
        if OTHER_COINS.search(t):
            return 1
        return 0

    items.sort(key=lambda n: (score(n), n["time"]), reverse=True)
    return items[:MAX_NEWS]


def _engines():
    from deep_translator import GoogleTranslator, MyMemoryTranslator

    return [
        ("google", GoogleTranslator(source="en", target="hi")),
        ("mymemory", MyMemoryTranslator(source="en-GB", target="hi-IN")),
    ]


def to_hindi(titles):
    """Har headline ka Hindi tarjuma. Ek translator fail ho to doosra try hota hai."""
    try:
        engines = _engines()
    except Exception as e:
        print("Translator load fail:", e)
        return [None] * len(titles)
    out = []
    for t in titles:
        res = None
        for name, tr in list(engines):
            try:
                r = tr.translate(t)
                if r and r.strip() and "MYMEMORY WARNING" not in r.upper():
                    res = r.strip()
                    break
                print(f"Tarjuma khali/limit ({name})")
            except Exception as e:
                print(f"Tarjuma fail ({name}):", str(e)[:80])
            if engines and engines[0][0] == name:
                engines.append(engines.pop(0))  # fail hone wala translator peeche
        out.append(res)
        time.sleep(0.4)
    print(f"Tarjuma: {sum(1 for x in out if x)}/{len(out)}")
    return out


def build_segments():
    """[(lang, tld, text), ...] : Hindi mein, jahan tarjuma na ho wahan English mein."""
    news = pick_news()
    segs = [("hi", "com", "सुप्रभात। यह आज की ताज़ा क्रिप्टो ख़बरें हैं।")]
    if not news:
        segs.append(("hi", "com", "पिछले चौबीस घंटे में कोई ख़ास ख़बर नहीं मिली।"))
    else:
        hindi = to_hindi([n["title"] for n in news])
        sums_hi = iter(to_hindi([n["summary"] for n in news if n["summary"]]))
        for i, (n, h) in enumerate(zip(news, hindi)):
            label = f"{ORDINALS[i]} ख़बर।"
            sh = next(sums_hi) if n["summary"] else None
            if h:
                segs.append(("hi", "com", f"{label} {h}" + (f" {sh}" if sh else "")))
            else:
                segs.append(("hi", "com", label))
                segs.append(("en", "co.in", n["title"]))
                if sh:
                    segs.append(("hi", "com", sh))
    segs.append(("hi", "com", macro.audio_line()))
    segs.append(("hi", "com", "पूरी ख़बरें और लिंक ईमेल में हैं। यह सिर्फ़ जानकारी है, ट्रेडिंग की सलाह नहीं।"))
    return segs


def build_mp3_b64():
    from gtts import gTTS

    buf = io.BytesIO()
    for lang, tld, text in build_segments():
        gTTS(text, lang=lang, tld=tld).write_to_fp(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")
