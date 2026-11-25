"""Subah ki report ka Hindi audio (MP3), gTTS se (free, bina key ke)."""
import base64
import io

import report

NAMES = {"BTC": "बिटकॉइन", "ETH": "एथेरियम", "SOL": "सोलाना"}


def num(p):
    return str(round(p)) if p >= 1000 else f"{p:.2f}"


def direction(x):
    return "ऊपर" if x >= 0 else "नीचे"


def build_script():
    parts = ["सुप्रभात। यह आज की क्रिप्टो रिपोर्ट है।"]
    for sym, pair in report.COINS.items():
        name = NAMES.get(sym, sym)
        try:
            c = report.kraken_ohlc(pair, 1440)
        except Exception as e:
            print("Audio data fail:", sym, e)
            parts.append(f"{name} का डेटा अभी नहीं मिला।")
            continue
        today, yest = c[-1], c[-2]
        now = today[4]
        t = (now - today[1]) / today[1] * 100
        y = (yest[4] - yest[1]) / yest[1] * 100
        parts.append(
            f"{name}। मौजूदा क़ीमत {num(now)} डॉलर है। "
            f"आज की ओपनिंग से यह {abs(t):.1f} प्रतिशत {direction(t)} है। "
            f"कल की क्लोज़िंग {num(yest[4])} डॉलर रही, "
            f"और कल यह {abs(y):.1f} प्रतिशत {direction(y)} रहा।"
        )
    parts.append("ताज़ा ख़बरें और पूरी जानकारी ईमेल में देखें। यह सिर्फ़ जानकारी है, ट्रेडिंग की सलाह नहीं।")
    return " ".join(parts)


def build_mp3_b64():
    from gtts import gTTS

    buf = io.BytesIO()
    gTTS(build_script(), lang="hi").write_to_fp(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")
