"""Subah ki khabron ka Hindi audio (MP3). gTTS + deep-translator (dono free, bina key ke)."""
import base64
import io
import re
from datetime import datetime, timedelta, timezone

import report

ORDINALS = ["पहली", "दूसरी", "तीसरी", "चौथी", "पाँचवीं", "छठी", "सातवीं", "आठवीं"]
MAX_NEWS = 8
OTHER_COINS = re.compile(r"\b(ethereum|ether|eth|solana|sol)\b", re.I)


def pick_news():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    items = [n for n in report.get_news() if n["time"] >= cutoff]

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


def to_hindi(titles):
    """Har headline ka Hindi tarjuma. Fail ho to us ki jagah None."""
    try:
        from deep_translator import GoogleTranslator

        tr = GoogleTranslator(source="en", target="hi")
    except Exception as e:
        print("Translator load fail:", e)
        return [None] * len(titles)
    out = []
    for t in titles:
        try:
            out.append(tr.translate(t))
        except Exception as e:
            print("Tarjuma fail:", e)
            out.append(None)
    return out


def build_segments():
    """[(lang, tld, text), ...] : Hindi mein, jahan tarjuma na ho wahan English mein."""
    news = pick_news()
    segs = [("hi", "com", "सुप्रभात। यह आज की ताज़ा क्रिप्टो ख़बरें हैं।")]
    if not news:
        segs.append(("hi", "com", "पिछले चौबीस घंटे में कोई ख़ास ख़बर नहीं मिली।"))
    else:
        hindi = to_hindi([n["title"] for n in news])
        for i, (n, h) in enumerate(zip(news, hindi)):
            label = f"{ORDINALS[i]} ख़बर।"
            if h:
                segs.append(("hi", "com", f"{label} {h}"))
            else:
                segs.append(("hi", "com", label))
                segs.append(("en", "co.in", n["title"]))
    segs.append(("hi", "com", "पूरी ख़बरें और लिंक ईमेल में हैं। यह सिर्फ़ जानकारी है, ट्रेडिंग की सलाह नहीं।"))
    return segs


def build_mp3_b64():
    from gtts import gTTS

    buf = io.BytesIO()
    for lang, tld, text in build_segments():
        gTTS(text, lang=lang, tld=tld).write_to_fp(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")
