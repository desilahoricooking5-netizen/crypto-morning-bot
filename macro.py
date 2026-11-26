"""CPI aur FOMC ki tareekhein + taaza figures (free, static calendar se)."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import report

PKT = ZoneInfo("Asia/Karachi")

# Official BLS/Fed calendars se (ghalat na ho is liye bain-bain update karein).
# Format: (UTC date, Pakistan ke hisaab se wazahat)
CPI_DATES = [
    datetime(2026, 12, 10, 13, 30, tzinfo=timezone.utc),
    datetime(2027, 1, 14, 13, 30, tzinfo=timezone.utc),
    datetime(2027, 2, 11, 13, 30, tzinfo=timezone.utc),
]
FOMC_DATES = [
    (datetime(2026, 12, 8, tzinfo=timezone.utc), datetime(2026, 12, 9, 19, 0, tzinfo=timezone.utc)),
    (datetime(2027, 1, 27, tzinfo=timezone.utc), datetime(2027, 1, 28, 19, 0, tzinfo=timezone.utc)),
]

LAST_CPI = {"label": "October 2026 CPI (10 Nov 2026 ko jari hua)", "mom": "+0.4%", "core_mom": "+0.3%"}
LAST_FOMC = {"label": "27-28 October 2026 ki FOMC meeting", "decision": "rate 3.75% se 4.00% par barqarar"}


def _next(dates_utc):
    now = datetime.now(timezone.utc)
    for d in dates_utc:
        if d > now:
            return d
    return None


def next_cpi_pkt():
    d = _next(CPI_DATES)
    return d.astimezone(PKT) if d else None


def next_fomc_pkt():
    for start, decision in FOMC_DATES:
        if decision > datetime.now(timezone.utc):
            return start.astimezone(PKT), decision.astimezone(PKT)
    return None, None


def fmt(dt):
    return dt.strftime("%d %b, %I:%M %p") if dt else None


def summary_text():
    cpi = fmt(next_cpi_pkt())
    fstart, fdec = next_fomc_pkt()
    lines = [
        f"Aakhri CPI: {LAST_CPI['label']}, monthly {LAST_CPI['mom']} (core {LAST_CPI['core_mom']}).",
        f"Aakhri Fed faisla: {LAST_FOMC['label']} - {LAST_FOMC['decision']}.",
    ]
    if cpi:
        lines.append(f"Agli CPI: {cpi} (Pakistan time).")
    if fstart:
        lines.append(f"Agli Fed meeting: {fstart.strftime('%d %b')} se, faisla {fmt(fdec)} (Pakistan time).")
    return lines


def summary_html():
    rows = "".join(f"<li style='margin:4px 0'>{l}</li>" for l in summary_text())
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" bgcolor="{report_bg()}" '
        f'style="background:{report_bg()};border-radius:14px;margin-bottom:18px">'
        f'<tr><td style="padding:18px 20px">'
        f'<div style="font-size:12px;letter-spacing:2px;color:#facc15;font-weight:bold;margin-bottom:8px">'
        f'CPI &amp; FED CALENDAR</div>'
        f'<ul style="margin:0;padding-left:18px;color:#f1f5f9;font-size:14px">{rows}</ul>'
        f'</td></tr></table>'
    )


def report_bg():
    return "#1e293b"


def audio_line():
    cpi = fmt(next_cpi_pkt())
    fstart, fdec = next_fomc_pkt()
    s = (
        f"अब बात करते हैं ब्याज दर और महंगाई की। {LAST_CPI['label'].split('(')[0].strip()} में महंगाई "
        f"महीने दर महीने {LAST_CPI['mom']} बढ़ी। {LAST_FOMC['label']} में फ़ेड ने ब्याज दर स्थिर रखी, "
        f"फ़ैसला था: {LAST_FOMC['decision']}।"
    )
    if cpi:
        s += f" अगला महंगाई डेटा {cpi} पाकिस्तान टाइम पर आएगा।"
    if fstart:
        s += f" अगली फ़ेड मीटिंग {fstart.strftime('%d %b')} से शुरू होगी।"
    return s
