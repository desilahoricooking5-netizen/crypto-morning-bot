"""Khoobsurat subah ki report: numbering, har coin ka alag card, alag khabrein."""
import html as H
import re
from datetime import datetime, timedelta, timezone

import report

META = {
    "BTC": ("Bitcoin", "#f7931a"),
    "ETH": ("Ethereum", "#8ea2ff"),
    "SOL": ("Solana", "#14f195"),
}
KEYWORDS = {"BTC": "bitcoin|btc", "ETH": "ethereum|ether|eth", "SOL": "solana|sol"}
UP, DOWN, MUTED, TEXT = "#22c55e", "#ef4444", "#94a3b8", "#f1f5f9"
PAGE_BG, CARD_BG, LINE = "#0b1220", "#1e293b", "#334155"


def pct(a, b):
    return (a - b) / b * 100


def pill(p):
    col = UP if p >= 0 else DOWN
    arrow = "&#9650;" if p >= 0 else "&#9660;"
    return f'<span style="color:{col};font-weight:bold">{arrow} {p:+.2f}%</span>'


def row(label, value):
    return (
        f'<tr><td style="padding:5px 0;color:{MUTED};font-size:13px">{label}</td>'
        f'<td align="right" style="padding:5px 0;color:{TEXT};font-size:14px">{value}</td></tr>'
    )


def section(title, color, rows):
    return (
        f'<div style="margin:14px 0 4px;font-size:12px;letter-spacing:1px;'
        f'color:{color};font-weight:bold">{title}</div>'
        f'<table width="100%" cellpadding="0" cellspacing="0">{"".join(rows)}</table>'
    )


def coin_news(sym, items, limit=3):
    pat = re.compile(r"\b(" + KEYWORDS.get(sym, sym.lower()) + r")\b", re.I)
    return [n for n in items if pat.search(n["title"])][:limit]


def news_list_html(items, empty):
    if not items:
        return f'<div style="color:{MUTED};font-size:13px">{empty}</div>'
    out = ""
    for k, n in enumerate(items, 1):
        out += (
            f'<div style="margin:6px 0;font-size:14px;line-height:1.4">'
            f'<span style="color:{MUTED}">{k}.</span> '
            f'<a href="{H.escape(n["link"])}" style="color:#7dd3fc;text-decoration:none">'
            f'{H.escape(n["title"])}</a> '
            f'<span style="color:{MUTED};font-size:12px">({n["source"]})</span></div>'
        )
    return out


def coin_card(i, sym, c, news):
    name, color = META.get(sym, (sym, "#94a3b8"))
    today, yest = c[-1], c[-2]
    now = today[4]
    today_chg = pct(now, today[1])
    yest_chg = pct(yest[4], yest[1])
    yest_range = pct(yest[2], yest[3])
    week = pct(now, c[-8][4]) if len(c) >= 8 else None
    month = pct(now, c[-31][4]) if len(c) >= 31 else None

    rujhan = []
    if week is not None:
        rujhan.append(row("Pichle 7 din", pill(week)))
    if month is not None:
        rujhan.append(row("Pichle 30 din", pill(month)))

    card = (
        f'<table width="100%" cellpadding="0" cellspacing="0" bgcolor="{CARD_BG}" '
        f'style="background:{CARD_BG};border-radius:14px;border-left:6px solid {color};margin-bottom:18px">'
        f'<tr><td style="padding:18px 20px">'
        f'<div style="font-size:12px;color:{color};letter-spacing:2px;font-weight:bold">COIN {i}</div>'
        f'<div style="font-size:22px;color:#ffffff;font-weight:bold;margin-top:2px">{i}. {name} ({sym})</div>'
        f'<div style="font-size:32px;color:#ffffff;font-weight:bold;margin:10px 0 2px">{report.money(now)}</div>'
        f'<div style="font-size:14px">{pill(today_chg)} '
        f'<span style="color:{MUTED};font-size:12px">aaj ki open se</span></div>'
        f'<div style="border-top:1px solid {LINE};margin:14px 0 0"></div>'
        + section("AAJ (ABHI TAK)", color, [
            row("Aaj ki open", report.money(today[1])),
            row("Abhi ki price", report.money(now)),
            row("Aaj ka change", pill(today_chg)),
        ])
        + section("KAL KI CANDLE", color, [
            row("Open", report.money(yest[1])),
            row("High", report.money(yest[2])),
            row("Low", report.money(yest[3])),
            row("Close", report.money(yest[4])),
            row("Kal ka change", pill(yest_chg)),
            row("Kal ki range (high se low)", f"{yest_range:.2f}%"),
        ])
        + (section("RUJHAAN", color, rujhan) if rujhan else "")
        + f'<div style="margin:14px 0 4px;font-size:12px;letter-spacing:1px;color:{color};font-weight:bold">'
        f'{sym} KI TAAZA KHABRIEN</div>'
        + news_list_html(news, f"Pichle 24 ghante mein {sym} ki koi khaas khabar nahi mili.")
        + "</td></tr></table>"
    )
    text = (
        f"{i}. {name} ({sym}): {report.money(now)} ({today_chg:+.2f}% aaj ki open se)\n"
        f"   Aaj open {report.money(today[1])} | Kal open {report.money(yest[1])}, "
        f"high {report.money(yest[2])}, low {report.money(yest[3])}, close {report.money(yest[4])} "
        f"({yest_chg:+.2f}%)\n"
    )
    if week is not None:
        text += f"   7 din: {week:+.2f}%"
        text += f" | 30 din: {month:+.2f}%\n" if month is not None else "\n"
    for k, n in enumerate(news, 1):
        text += f"   {sym} khabar {k}: {n['title']} ({n['link']})\n"
    return card, text, now, today_chg


def error_card(i, sym, err):
    name, color = META.get(sym, (sym, "#94a3b8"))
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" bgcolor="{CARD_BG}" '
        f'style="background:{CARD_BG};border-radius:14px;border-left:6px solid {color};margin-bottom:18px">'
        f'<tr><td style="padding:18px 20px;color:{TEXT}">{i}. {name} ({sym}): data abhi nahi mila '
        f'<span style="color:{MUTED};font-size:12px">({H.escape(str(err))})</span></td></tr></table>'
    )


def morning():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    news = [n for n in report.get_news() if n["time"] >= cutoff]

    cards, texts, summary = "", "", []
    for i, (sym, pair) in enumerate(report.COINS.items(), 1):
        try:
            c = report.kraken_ohlc(pair, 1440)
            card, text, now, chg = coin_card(i, sym, c, coin_news(sym, news))
            cards += card
            texts += text + "\n"
            summary.append((sym, now, chg))
        except Exception as e:
            cards += error_card(i, sym, e)
            texts += f"{i}. {sym}: data nahi mila ({e})\n\n"

    # Ek nazar mein
    cells = ""
    for sym, now, chg in summary:
        color = META.get(sym, ("", "#94a3b8"))[1]
        cells += (
            f'<td align="center" style="padding:10px 6px">'
            f'<div style="color:{color};font-weight:bold;font-size:13px">{sym}</div>'
            f'<div style="color:#fff;font-size:16px;font-weight:bold">{report.money(now)}</div>'
            f'<div style="font-size:13px">{pill(chg)}</div></td>'
        )
    glance = (
        f'<table width="100%" cellpadding="0" cellspacing="0" bgcolor="{CARD_BG}" '
        f'style="background:{CARD_BG};border-radius:14px;margin-bottom:18px"><tr>{cells}</tr></table>'
        if cells else ""
    )

    used = {n["link"] for sym in report.COINS for n in coin_news(sym, news)}
    others = [n for n in news if n["link"] not in used][:6]

    body = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:{PAGE_BG}" bgcolor="{PAGE_BG}">
<table width="100%" cellpadding="0" cellspacing="0" bgcolor="{PAGE_BG}" style="background:{PAGE_BG}">
<tr><td align="center" style="padding:20px 10px">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;font-family:Arial,Helvetica,sans-serif">
<tr><td bgcolor="#312e81" style="background:#312e81;background-image:linear-gradient(135deg,#1e3a8a,#6d28d9);border-radius:16px;padding:24px 22px">
<div style="font-size:13px;color:#c7d2fe;letter-spacing:2px">SUBAH KI REPORT</div>
<div style="font-size:26px;color:#ffffff;font-weight:bold;margin:4px 0">Crypto Market Update</div>
<div style="font-size:13px;color:#c7d2fe">{report.pkt_now()} (Pakistan time)</div>
</td></tr>
<tr><td style="height:18px"></td></tr>
<tr><td>
<div style="color:{MUTED};font-size:12px;letter-spacing:2px;margin:0 0 8px 4px">EK NAZAR MEIN</div>
{glance}
{cards}
<table width="100%" cellpadding="0" cellspacing="0" bgcolor="{CARD_BG}" style="background:{CARD_BG};border-radius:14px;margin-bottom:18px">
<tr><td style="padding:18px 20px">
<div style="font-size:12px;letter-spacing:2px;color:#7dd3fc;font-weight:bold;margin-bottom:6px">BAQI MARKET KI KHABRIEN</div>
{news_list_html(others, "Koi aur taaza khabar nahi mili.")}
</td></tr></table>
<div style="color:{MUTED};font-size:11px;line-height:1.5;padding:0 6px 10px">
Candle UTC ke hisaab se hoti hai: Pakistan mein subah 5 baje se agle din subah 5 baje tak.
Ye maloomat sirf jaankari ke liye hai, trading ka mashwara nahi.
</div>
</td></tr></table>
</td></tr></table></body></html>"""

    head = "Subah ki Crypto Report"
    if summary:
        sym, now, chg = summary[0]
        head += f": {sym} {report.money(now)} ({chg:+.1f}%)"
    text_body = (
        f"Subah ki Crypto Report ({report.pkt_now()} PKT)\n\n{texts}"
        f"Baqi khabrein:\n{report.news_text(others)}\n"
    )
    report.send_email(head, body, text_body)
