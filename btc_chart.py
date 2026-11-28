"""
BTC morning chart: daily candles, EMA 21/50/100/200, SMA 50/200 (dashed),
golden/death cross markers, free "liquidity" levels (swing highs/lows,
previous day/week high/low), volume profile, and a rule-based Roman Urdu note.
Uses only pandas, numpy, matplotlib. No AI, no paid data.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

BG = "#000000"
PANEL = "#000000"
GRID = "#1f1f1f"
TEXT = "#e6e6e6"
UP = "#26c281"
DOWN = "#ef5350"
EMA_COLORS = {21: "#ffd166", 50: "#00e5ff", 100: "#b388ff", 200: "#ff8a65"}


# ----------------------------------------------------------------- indicators
def add_indicators(df):
    df = df.copy()
    for n in (21, 50, 100, 200):
        df[f"ema{n}"] = df["close"].ewm(span=n, adjust=False).mean()
    for n in (50, 200):
        df[f"sma{n}"] = df["close"].rolling(n).mean()
    return df


def find_crosses(fast, slow):
    """Return list of (index_position, 'golden'|'death')."""
    diff = (fast - slow).values
    out = []
    for i in range(1, len(diff)):
        if np.isnan(diff[i]) or np.isnan(diff[i - 1]):
            continue
        if diff[i - 1] <= 0 < diff[i]:
            out.append((i, "golden"))
        elif diff[i - 1] >= 0 > diff[i]:
            out.append((i, "death"))
    return out


def swing_points(df, window=5):
    hi, lo = [], []
    h, l = df["high"].values, df["low"].values
    for i in range(window, len(df) - window):
        if h[i] == h[i - window:i + window + 1].max():
            hi.append((i, h[i]))
        if l[i] == l[i - window:i + window + 1].min():
            lo.append((i, l[i]))
    return hi, lo


def liquidity_levels(df, lookback=120):
    """Free proxy for liquidity: where stop orders usually sit."""
    d = df.iloc[-lookback:].reset_index(drop=True)
    price = d["close"].iloc[-1]
    hi, lo = swing_points(d, 4)
    highs = sorted({round(v, -1) for _, v in hi if v > price})[:3]
    lows = sorted({round(v, -1) for _, v in lo if v < price}, reverse=True)[:3]
    prev = df.iloc[-2]
    week = df.iloc[-8:-1]
    levels = [("PDH", prev["high"]), ("PDL", prev["low"]),
              ("PWH", week["high"].max()), ("PWL", week["low"].min())]
    return highs, lows, levels


def volume_profile(df, lookback=90, bins=40):
    d = df.iloc[-lookback:]
    lo, hi = d["low"].min(), d["high"].max()
    edges = np.linspace(lo, hi, bins + 1)
    mids = (edges[:-1] + edges[1:]) / 2
    vol = np.zeros(bins)
    for _, r in d.iterrows():
        typical = (r["high"] + r["low"] + r["close"]) / 3
        k = min(np.searchsorted(edges, typical, side="right") - 1, bins - 1)
        vol[max(k, 0)] += r["volume"]
    return mids, vol, edges


def key_levels(df, min_gap=0.012):
    """Nearest 2 supports and 2 resistances from swings, week hi/lo, POC and EMAs."""
    last = df.iloc[-1]
    p = last["close"]
    highs, lows, levels = liquidity_levels(df)
    mids, vol, _ = volume_profile(df)
    cands = list(highs) + list(lows)
    cands += [v for name, v in levels if name in ("PWH", "PWL")]
    cands += [mids[int(np.argmax(vol))]]
    cands += [last[f"ema{n}"] for n in (21, 50, 100, 200)]

    def pick(vals, reverse):
        out = []
        for v in sorted(vals, reverse=reverse):
            if all(abs(v / o - 1) >= min_gap for o in out):
                out.append(v)
            if len(out) == 2:
                break
        return out
    res = pick([v for v in cands if v > p * (1 + min_gap / 2)], False)
    sup = pick([v for v in cands if v < p * (1 - min_gap / 2)], True)
    while len(res) < 2:
        res.append((res[-1] if res else p) * 1.03)
    while len(sup) < 2:
        sup.append((sup[-1] if sup else p) * 0.97)
    return sup, res


# ------------------------------------------------------------------- analysis
def fmt(x):
    return f"{x:,.0f}"


def build_analysis(df):
    """Rule-based Roman Urdu note. Not a prediction, not advice."""
    last = df.iloc[-1]
    p = last["close"]
    e = {n: last[f"ema{n}"] for n in (21, 50, 100, 200)}
    above = [n for n in e if p > e[n]]
    below = [n for n in e if p <= e[n]]

    if not above:
        trend = "Qeemat chaaron EMAs (21, 50, 100, 200) se NEECHE hai, yani trend kamzor (bearish) hai."
    elif len(above) == 4:
        trend = "Qeemat chaaron EMAs se UPAR hai, yani trend mazboot (bullish) hai."
    else:
        trend = ("Qeemat kuch EMAs ke upar aur kuch ke neeche hai (upar: "
                 + ", ".join(map(str, sorted(above))) + "; neeche: "
                 + ", ".join(map(str, sorted(below))) + "), yani market mili-juli (mixed) hai.")

    aligned_bear = e[21] < e[50] < e[100] < e[200]
    aligned_bull = e[21] > e[50] > e[100] > e[200]
    align = ("EMAs ki tarteeb bearish hai (21 < 50 < 100 < 200)." if aligned_bear else
             "EMAs ki tarteeb bullish hai (21 > 50 > 100 > 200)." if aligned_bull else
             "EMAs ki tarteeb mili-juli hai, koi saaf rujhan nahi.")

    ema_state = "death cross (50 EMA, 200 EMA se neeche)" if e[50] < e[200] else "golden cross (50 EMA, 200 EMA se upar)"
    s50, s200 = last["sma50"], last["sma200"]
    sma_state = "death cross (50 SMA, 200 SMA se neeche)" if s50 < s200 else "golden cross (50 SMA, 200 SMA se upar)"

    sup, res = key_levels(df)
    s1, s2 = sup
    r1, r2 = res

    lines = [
        f"Kal ki close: {fmt(p)} dollar.",
        trend,
        align,
        f"EMA ke hisaab se: {ema_state}. SMA ke hisaab se: {sma_state}.",
        f"Qeemat 200 EMA ({fmt(e[200])}) se {abs(p / e[200] - 1) * 100:.1f}% "
        f"{'neeche' if p < e[200] else 'upar'} hai, aur 50 EMA ({fmt(e[50])}) se {abs(p / e[50] - 1) * 100:.1f}% "
        f"{'neeche' if p < e[50] else 'upar'}.",
        f"Qareebi support: {fmt(s1)} aur {fmt(s2)}. Qareebi resistance: {fmt(r1)} aur {fmt(r2)}.",
        "",
        "Aage ke imkanaat (andaza nahi, sirf 'agar...to'):",
        f"1) Upar ka raasta: agar qeemat {fmt(r1)} ke upar band ho, to {fmt(r2)} ki taraf barhne ka imkan banta hai.",
        f"2) Side-ways: agar {fmt(s1)} se {fmt(r1)} ke andar rahe, to kuch din range-bound rehne ka imkan hai.",
        f"3) Neeche ka raasta: agar {fmt(s1)} ke neeche band ho, to {fmt(s2)} ki taraf giravat ka imkan banta hai.",
        "",
        "Ye maloomat hai, trading ka mashwara nahi. Moving averages pichli qeematon se banti hain, is liye lagging hain.",
    ]
    return "\n".join(lines)


# ------------------------------------------------------------------------ plot
def plot_chart(df, path, title="BTC/USD Daily", show=130, sample=False):
    df = add_indicators(df)
    n = len(df)
    start = n - show
    d = df.iloc[start:].reset_index(drop=True)
    x = np.arange(len(d))
    price = d["close"].iloc[-1]

    fig = plt.figure(figsize=(14, 9), facecolor=BG)
    gs = fig.add_gridspec(2, 2, width_ratios=[5.2, 1], height_ratios=[4, 1],
                          hspace=0.04, wspace=0.03,
                          left=0.06, right=0.97, top=0.90, bottom=0.07)
    ax = fig.add_subplot(gs[0, 0], facecolor=PANEL)
    axv = fig.add_subplot(gs[1, 0], facecolor=PANEL, sharex=ax)
    axp = fig.add_subplot(gs[0, 1], facecolor=PANEL, sharey=ax)

    # candles
    for i, r in d.iterrows():
        c = UP if r["close"] >= r["open"] else DOWN
        ax.vlines(i, r["low"], r["high"], color=c, linewidth=0.9, zorder=3)
        ax.add_patch(Rectangle((i - 0.32, min(r["open"], r["close"])), 0.64,
                               max(abs(r["close"] - r["open"]), price * 0.0003),
                               facecolor=c, edgecolor=c, zorder=4))

    # EMAs
    for k, col in EMA_COLORS.items():
        ax.plot(x, d[f"ema{k}"], color=col, linewidth=1.6 if k in (50, 200) else 1.2,
                label=f"EMA {k}", zorder=5)
    # SMAs dashed
    ax.plot(x, d["sma50"], color="#00e5ff", linewidth=1.0, linestyle=(0, (4, 3)),
            alpha=0.85, label="SMA 50", zorder=5)
    ax.plot(x, d["sma200"], color="#ff8a65", linewidth=1.0, linestyle=(0, (4, 3)),
            alpha=0.85, label="SMA 200", zorder=5)

    # crosses (computed on full history, drawn if inside window)
    for (fast, slow, tag) in (("ema50", "ema200", "EMA"), ("sma50", "sma200", "SMA")):
        for i, kind in find_crosses(df[fast], df[slow]):
            j = i - start
            if 0 <= j < len(d):
                y = d[slow].iloc[j]
                ax.scatter(j, y, s=140, marker="v" if kind == "death" else "^",
                           color=DOWN if kind == "death" else UP, edgecolor="white",
                           linewidth=0.8, zorder=8)
                ax.annotate(f"{tag} {kind} cross", (j, y), xytext=(0, -22 if kind == "death" else 18),
                            textcoords="offset points", ha="center", fontsize=8.5,
                            color="white", zorder=9)

    # liquidity levels
    highs, lows, levels = liquidity_levels(df)
    xr = len(d) + 13
    for v in highs:
        ax.axhline(v, color="#ff6b6b", linewidth=0.9, linestyle=(0, (2, 3)), alpha=0.8, zorder=2)
        if abs(v / price - 1) > 0.012:
            ax.text(xr, v, f"BSL {fmt(v)}", color="#ff6b6b", fontsize=8, va="bottom", ha="right")
    for v in lows:
        ax.axhline(v, color="#4dd0e1", linewidth=0.9, linestyle=(0, (2, 3)), alpha=0.8, zorder=2)
        if abs(v / price - 1) > 0.012:
            ax.text(xr, v, f"SSL {fmt(v)}", color="#4dd0e1", fontsize=8, va="top", ha="right")
    for name, v in levels:
        if name in ("PWH", "PWL"):
            ax.axhline(v, color="#a9b4c8", linewidth=0.7, linestyle="-", alpha=0.45, zorder=2)
            ax.text(1, v, f"{name} {fmt(v)}", color="#a9b4c8", fontsize=7.5,
                    va="bottom" if name == "PWH" else "top", ha="left")

    # volume profile (right)
    mids, vol, edges = volume_profile(df)
    axp.barh(mids, vol, height=(edges[1] - edges[0]) * 0.9, color="#5b6b8c", alpha=0.75)
    poc = mids[int(np.argmax(vol))]
    axp.axhline(poc, color="#ffd166", linewidth=1.2)
    axp.text(vol.max() * 0.98, poc, "POC", color="#ffd166", fontsize=8, va="bottom", ha="right")
    ax.axhline(poc, color="#ffd166", linewidth=0.8, linestyle=(0, (6, 4)), alpha=0.6, zorder=2)

    # current price tag
    ax.axhline(price, color="white", linewidth=0.8, alpha=0.5, zorder=2)
    ax.annotate(f" {fmt(price)} ", (len(d) - 1, price), xytext=(6, 0), textcoords="offset points",
                color="black", fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor="none"))

    # key levels panel
    axk = fig.add_subplot(gs[1, 1], facecolor=PANEL)
    axk.set_xticks([])
    axk.set_yticks([])
    for sp in axk.spines.values():
        sp.set_color(GRID)
    sup, res = key_levels(df)
    last = d.iloc[-1]
    rows = [("Resistance 2", res[1], "#ff6b6b"), ("Resistance 1", res[0], "#ff6b6b"),
            ("Qeemat", price, "white"),
            ("Support 1", sup[0], "#4dd0e1"), ("Support 2", sup[1], "#4dd0e1")]
    y0 = 0.90
    for name, v, col in rows:
        axk.text(0.06, y0, name, color=col, fontsize=7.5, transform=axk.transAxes, va="center")
        axk.text(0.94, y0, fmt(v), color=col, fontsize=7.5, transform=axk.transAxes, va="center", ha="right")
        y0 -= 0.14
    est = "DEATH" if last["ema50"] < last["ema200"] else "GOLDEN"
    sst = "DEATH" if last["sma50"] < last["sma200"] else "GOLDEN"
    axk.text(0.06, 0.12, f"EMA 50/200: {est}", color="#ffd166", fontsize=7.5, transform=axk.transAxes, va="center")
    axk.text(0.06, 0.03, f"SMA 50/200: {sst}", color="#ffd166", fontsize=7.5, transform=axk.transAxes, va="center")

    # volume bars
    axv.bar(x, d["volume"], color=[UP if c >= o else DOWN for c, o in zip(d["close"], d["open"])],
            width=0.7, alpha=0.75)
    axv.set_ylabel("Volume", color=TEXT, fontsize=8)

    # axes styling
    for a in (ax, axv, axp):
        a.tick_params(colors=TEXT, labelsize=8)
        for s in a.spines.values():
            s.set_color(GRID)
        a.grid(color=GRID, linewidth=0.5, alpha=0.7)
    plt.setp(ax.get_xticklabels(), visible=False)
    plt.setp(axp.get_yticklabels(), visible=False)
    plt.setp(axp.get_xticklabels(), visible=False)
    axp.set_title("Volume profile", color=TEXT, fontsize=8, pad=3)
    ax.set_xlim(-1, len(d) + 14)
    ymax = max(d["high"].max(), d["ema200"].iloc[-1], d["sma200"].iloc[-1], d["ema100"].iloc[-1])
    ymin = d["low"].min()
    pad = (ymax - ymin) * 0.07
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))

    step = max(len(d) // 8, 1)
    ticks = list(range(0, len(d), step))
    axv.set_xticks(ticks)
    axv.set_xticklabels([pd.Timestamp(d["date"].iloc[i]).strftime("%d %b") for i in ticks],
                        color=TEXT, fontsize=8)

    leg = ax.legend(loc="upper left", ncol=3, fontsize=8, facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT)
    for t in leg.get_texts():
        t.set_color(TEXT)

    fig.text(0.06, 0.945, title, color="white", fontsize=17, fontweight="bold")
    last_date = pd.Timestamp(d["date"].iloc[-1]).strftime("%d %b %Y")
    sub = f"Kal ki daily close tak (UTC): {last_date}  |  BSL = upar ki liquidity (stops), SSL = neeche ki liquidity, POC = sab se zyada volume"
    fig.text(0.06, 0.915, sub, color="#a9b4c8", fontsize=9)
    if sample:
        fig.text(0.5, 0.5, "SAMPLE DATA", color="white", alpha=0.07, fontsize=90,
                 fontweight="bold", ha="center", va="center", rotation=20)
        fig.text(0.97, 0.945, "SAMPLE DATA - asli nahi", color="#ffb74d", fontsize=10,
                 fontweight="bold", ha="right")
    fig.text(0.97, 0.012, "Maloomat hai, mashwara nahi. Lagging indicators.", color="#7a8599",
             fontsize=7.5, ha="right")
    fig.savefig(path, dpi=130, facecolor=BG)
    plt.close(fig)
    return build_analysis(df)


# ------------------------------------------------------------------ live data
def fetch_candles(pair="XBTUSD", interval=1440):
    """Kraken public OHLC (free). Aakhri adhoori candle hata di jati hai."""
    import json
    import urllib.request
    req = urllib.request.Request(
        f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}",
        headers={"User-Agent": "crypto-morning-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    if data.get("error"):
        raise RuntimeError(str(data["error"]))
    res = data["result"]
    key = [k for k in res if k != "last"][0]
    rows = res[key][:-1]  # chal rahi candle nikal di
    df = pd.DataFrame(rows, columns=["t", "open", "high", "low", "close", "vwap", "volume", "count"])
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    df["date"] = pd.to_datetime(df["t"].astype(int), unit="s")
    return df[["date", "open", "high", "low", "close", "volume"]]


def build_btc_report(path="btc-chart.png", pair="XBTUSD"):
    """Chart PNG banata hai aur Roman Urdu tajziya (text) wapas deta hai."""
    df = fetch_candles(pair)
    if len(df) < 260:
        raise RuntimeError(f"Kam candles mili: {len(df)}")
    return plot_chart(df, path, title="BTC/USD  Daily  -  EMA 21/50/100/200 + Liquidity")
