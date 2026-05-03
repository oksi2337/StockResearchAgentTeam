from __future__ import annotations
import os
import traceback
import asyncio
import aiohttp
import discord
import requests
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

SYMBOL_TO_ID = {
    "^DJI": "dji", "^GSPC": "gspc", "^IXIC": "ixic",
    "^RUT": "rut", "^SOX": "sox", "^VIX": "vix",
    "CL=F": "wti", "GC=F": "gold", "DX-Y.NYB": "dxy",
    "^IRX": "us2y", "^TNX": "us10y", "KRW=X": "usdkrw",
    "^KS11": "kospi", "^KQ11": "kosdaq",
}


def _fetch_yahoo_bulk() -> dict:
    """yf.download 배치 수집. 실패 시 빈 dict 반환."""
    symbols = list(SYMBOL_TO_ID.keys())
    raw = yf.download(symbols, period="10d", auto_adjust=True, progress=False)
    if raw.empty:
        raise ValueError("빈 DataFrame 반환")
    if hasattr(raw.columns, "levels"):
        close = raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw
    else:
        close = raw["Close"] if "Close" in raw.columns else raw
    out = {}
    for symbol, id_ in SYMBOL_TO_ID.items():
        if not hasattr(close, "columns") or symbol not in close.columns:
            print(f"[야후] {symbol} 컬럼 없음")
            continue
        series = close[symbol].dropna()
        if len(series) < 2:
            print(f"[야후] {symbol} 데이터 부족 ({len(series)}행)")
            continue
        curr = float(series.iloc[-1])
        prev = float(series.iloc[-2])
        change_pct = (curr - prev) / prev * 100 if prev else 0
        out[id_] = {"value": curr, "change": curr - prev, "change_pct": change_pct}
    return out


def _fetch_yahoo_single(symbol: str, id_: str) -> tuple[str, dict] | None:
    """단일 종목 수집 (배치 실패 시 폴백)."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="10d", auto_adjust=True)
        if hist.empty or len(hist) < 2:
            return None
        curr = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])
        change_pct = (curr - prev) / prev * 100 if prev else 0
        return id_, {"value": curr, "change": curr - prev, "change_pct": change_pct}
    except Exception as e:
        print(f"[야후 단일] {symbol} 실패: {e}")
        return None


def _fetch_yahoo() -> dict:
    try:
        out = _fetch_yahoo_bulk()
        if out:
            return out
        print("[야후] 배치 수집 결과 없음 → 단일 수집으로 전환")
    except Exception as e:
        print(f"[야후] 배치 수집 실패: {e} → 단일 수집으로 전환")

    out = {}
    for symbol, id_ in SYMBOL_TO_ID.items():
        result = _fetch_yahoo_single(symbol, id_)
        if result:
            out[result[0]] = result[1]
    return out


def _fetch_fear_greed() -> dict | None:
    try:
        r = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={"User-Agent": UA},
            timeout=10,
        )
        r.raise_for_status()
        fg = r.json().get("fear_and_greed", {})
        score = round(fg.get("score", 0))
        prev = round(fg.get("previous_close", score))
        return {"score": score, "rating": fg.get("rating", ""), "change": score - prev}
    except Exception as e:
        print(f"[CNN F&G] 수집 실패: {e}")
        return None


def _fetch_fred(series_id: str, id_: str, api_key: str) -> dict | None:
    try:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={api_key}&limit=5&sort_order=desc&file_type=json"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        obs = [o for o in r.json().get("observations", []) if o["value"] != "."]
        if len(obs) < 2:
            return None
        curr, prev = float(obs[0]["value"]), float(obs[1]["value"])
        change_pct = ((curr - prev) / abs(prev) * 100) if prev else 0
        return {"id": id_, "value": curr, "change": curr - prev, "change_pct": change_pct, "date": obs[0]["date"]}
    except Exception as e:
        print(f"[FRED {series_id}] 수집 실패: {e}")
        return None


def _fetch_naver_adv_dec(market: str) -> dict | None:
    try:
        r = requests.get(
            f"https://m.stock.naver.com/api/index/{market}/basic",
            headers={"User-Agent": UA},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "advance": data.get("riseCount", 0),
            "decline": data.get("fallCount", 0),
            "unchanged": data.get("unchangeCount", 0),
        }
    except Exception as e:
        print(f"[Naver {market}] 수집 실패: {e}")
        return None


def fetch_all() -> dict:
    fred_key = os.getenv("FRED_API_KEY") or os.getenv("EXPO_PUBLIC_FRED_API_KEY", "")
    quotes = _fetch_yahoo()
    fear_greed = _fetch_fear_greed()

    fred_data = {}
    if fred_key:
        tips = _fetch_fred("DFII10", "tips10y", fred_key)
        hy = _fetch_fred("BAMLH0A0HYM2", "hy_spread", fred_key)
        if tips:
            fred_data["tips10y"] = tips
        if hy:
            fred_data["hy_spread"] = hy

    return {
        "quotes": quotes,
        "fear_greed": fear_greed,
        "fred": fred_data,
        "kospi_adv": _fetch_naver_adv_dec("KOSPI"),
        "kosdaq_adv": _fetch_naver_adv_dec("KOSDAQ"),
        "fetched_at": datetime.now().isoformat(),
    }


def _fmt(value: float, change_pct: float, unit: str = "", decimals: int = 2) -> str:
    arrow = "▲" if change_pct >= 0 else "▼"
    if unit == "%":
        val = f"{value:.{decimals}f}%"
    elif unit == "원":
        val = f"{value:,.0f}원"
    elif unit == "$":
        val = f"${value:,.{decimals}f}"
    elif unit == "pt":
        val = f"{value:,.{decimals}f}"
    else:
        val = f"{value:,.{decimals}f}"
    return f"{val}  {arrow} {abs(change_pct):.2f}%"


def _fg_label(score: int) -> str:
    if score <= 25:
        return "극도 공포"
    if score <= 45:
        return "공포"
    if score <= 55:
        return "중립"
    if score <= 75:
        return "탐욕"
    return "극도 탐욕"


def _fg_color(score: int) -> int:
    if score <= 25:
        return 0xDC2626
    if score <= 45:
        return 0xF97316
    if score <= 55:
        return 0xA3A3A3
    if score <= 75:
        return 0x4ADE80
    return 0x16A34A


def build_embeds(data: dict) -> list[discord.Embed]:
    q = data.get("quotes", {})
    fg = data.get("fear_greed")
    fred = data.get("fred", {})
    ka = data.get("kospi_adv")
    da = data.get("kosdaq_adv")
    fetched = data.get("fetched_at", "")
    ts = datetime.fromisoformat(fetched) if fetched else datetime.now()

    # ── Embed 1: 글로벌 지수 & 변동성 ──
    e1 = discord.Embed(title="🌐 글로벌 지수 · 변동성", color=0x2563EB, timestamp=ts)

    for id_, name, unit, dec in [
        ("dji",  "다우존스",         "pt", 2),
        ("gspc", "S&P 500",         "pt", 2),
        ("ixic", "나스닥",           "pt", 2),
        ("rut",  "러셀 2000",        "pt", 2),
        ("sox",  "필라델피아 반도체", "pt", 2),
        ("vix",  "VIX",             "",   2),
    ]:
        if id_ in q:
            e1.add_field(name=name, value=_fmt(q[id_]["value"], q[id_]["change_pct"], unit, dec), inline=True)

    if fg:
        score = fg["score"]
        arrow = "▲" if fg.get("change", 0) >= 0 else "▼"
        e1.add_field(
            name="공포탐욕지수 (CNN)",
            value=f"**{score}**  {arrow} {abs(fg.get('change', 0))}pt  —  {_fg_label(score)}",
            inline=False,
        )

    # ── Embed 2: 금리 & 통화/원자재 ──
    e2 = discord.Embed(title="💰 금리 · 통화 · 원자재", color=0x16A34A, timestamp=ts)

    for id_, name, unit, dec in [
        ("us2y",  "미 2년물 국채",  "%", 3),
        ("us10y", "미 10년물 국채", "%", 3),
    ]:
        if id_ in q:
            e2.add_field(name=name, value=_fmt(q[id_]["value"], q[id_]["change_pct"], unit, dec), inline=True)

    for id_, name in [("tips10y", "실질금리 TIPS"), ("hy_spread", "HY 스프레드")]:
        if id_ in fred:
            e2.add_field(
                name=f"{name} (FRED)",
                value=_fmt(fred[id_]["value"], fred[id_].get("change_pct", 0), "%", 2),
                inline=True,
            )

    for id_, name, unit, dec in [
        ("dxy",    "달러 인덱스", "",    2),
        ("usdkrw", "원/달러",     "원",  0),
        ("wti",    "WTI 원유",    "$",   2),
        ("gold",   "금",          "$",   2),
    ]:
        if id_ in q:
            e2.add_field(name=name, value=_fmt(q[id_]["value"], q[id_]["change_pct"], unit, dec), inline=True)

    # ── Embed 3: 한국 시장 ──
    e3 = discord.Embed(title="🇰🇷 한국 시장", color=0xDC2626, timestamp=ts)

    for id_, name, unit, dec in [
        ("kospi",  "코스피", "pt", 2),
        ("kosdaq", "코스닥", "pt", 2),
    ]:
        if id_ in q:
            e3.add_field(name=name, value=_fmt(q[id_]["value"], q[id_]["change_pct"], unit, dec), inline=True)

    if ka:
        e3.add_field(
            name="코스피 등락",
            value=f"▲ 상승 **{ka['advance']}**  |  ▼ 하락 **{ka['decline']}**  |  — 보합 **{ka['unchanged']}**",
            inline=False,
        )
    if da:
        e3.add_field(
            name="코스닥 등락",
            value=f"▲ 상승 **{da['advance']}**  |  ▼ 하락 **{da['decline']}**  |  — 보합 **{da['unchanged']}**",
            inline=False,
        )

    sources = "Yahoo Finance · CNN Fear & Greed · Naver Finance"
    if fred:
        sources += " · FRED"
    e3.set_footer(text=f"수집: {ts.strftime('%Y-%m-%d %H:%M')} KST  |  {sources}")

    return [e1, e2, e3]


async def _send_embeds(channel_id: int, embeds: list[discord.Embed]) -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}
    payload = {"embeds": [e.to_dict() for e in embeds]}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers=headers,
            json=payload,
        ) as resp:
            if resp.status not in (200, 201):
                print(f"[Discord 지표] 전송 실패: {resp.status}")


async def run_global() -> None:
    """글로벌 지수·변동성·금리·통화·원자재 Embed 1~2 → #일간-요약 (매일 07:00)"""
    ch = int(os.getenv("DISCORD_CH_DAILY_SUMMARY"))
    data = fetch_all()
    embeds = build_embeds(data)
    await _send_embeds(ch, embeds[:2])
    print("[지표] 글로벌 지수·금리·통화·원자재 전송 완료")


async def run_korea() -> None:
    """한국 시장 지표 Embed 3 → #일간-요약 (매일 15:31, 당일 마감 데이터)"""
    ch = int(os.getenv("DISCORD_CH_DAILY_SUMMARY"))
    data = fetch_all()
    embeds = build_embeds(data)
    await _send_embeds(ch, embeds[2:])
    print("[지표] 한국 시장 지표 전송 완료")


if __name__ == "__main__":
    import json
    data = fetch_all()
    print(json.dumps({k: v for k, v in data.items() if k != "fear_greed"}, ensure_ascii=False, indent=2))
    if data["fear_greed"]:
        print(f"공포탐욕: {data['fear_greed']}")
