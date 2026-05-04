"""
Korean Market Report — 매일 16:00 (국장 마감 30분 후) 실행
Yahoo Finance는 마감 후 즉시 갱신되지 않으므로 당일 종가 반영까지 대기 후 수집.
KOSPI 시총 상위 20 (실시간) + 워치리스트 종목 분석 → #일간-요약 채널 전송
"""
from __future__ import annotations
import os
import json
import asyncio
import aiohttp
import yfinance as yf
import FinanceDataReader as fdr
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CH_DAILY_SUMMARY = int(os.getenv("DISCORD_CH_DAILY_SUMMARY"))
CH_MARKET_ALERT = int(os.getenv("DISCORD_CH_MARKET_ALERT"))
WATCHLIST_PATH = Path(__file__).parent.parent / "data" / "watchlist.json"

DISCORD_API = "https://discord.com/api/v10"
KOSPI_TOP_N = 20

KR_INDICES = {
    "^KS11": "KOSPI",
    "^KQ11": "KOSDAQ",
}


async def send_embed(channel_id: int, embed: dict):
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            headers=headers,
            json={"embeds": [embed]},
        ) as resp:
            if resp.status not in (200, 201):
                print(f"[Discord] 전송 실패: {resp.status}")


def fetch_kospi_top(n: int = KOSPI_TOP_N) -> dict:
    """KOSPI 시총 상위 N개 실시간 조회"""
    try:
        df = fdr.StockListing("KOSPI")
        # 시총 기준 정렬
        if "Marcap" in df.columns:
            df = df.sort_values("Marcap", ascending=False)
        elif "MarketCap" in df.columns:
            df = df.sort_values("MarketCap", ascending=False)
        top = df.head(n)
        result = {}
        for _, row in top.iterrows():
            code = str(row.get("Code", row.get("Symbol", ""))).zfill(6)
            name = row.get("Name", code)
            ticker = f"{code}.KS"
            result[ticker] = name
        print(f"[국장] KOSPI 시총 상위 {len(result)}개 조회 완료")
        return result
    except Exception as e:
        print(f"[국장] KOSPI 시총 조회 실패: {e}")
        return {}


def get_index_data(ticker: str) -> dict | None:
    try:
        idx = yf.Ticker(ticker)
        hist = idx.history(period="5d")
        if hist.empty or len(hist) < 2:
            return None
        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])
        return {"current": current, "change": (current - prev) / prev * 100}
    except Exception as e:
        print(f"[국장] {ticker} 지수 수집 실패: {e}")
        return None


def get_stock_data(ticker: str) -> dict | None:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if hist.empty or len(hist) < 2:
            return None
        current = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])
        return {
            "current": current,
            "change": (current - prev) / prev * 100,
            "volume": int(hist["Volume"].iloc[-1]),
        }
    except Exception as e:
        print(f"[국장] {ticker} 수집 실패: {e}")
        return None


KST = timezone(timedelta(hours=9))
_MAX_WAIT_MINUTES = 20
_RETRY_INTERVAL_SEC = 180  # 3분


def wait_for_today_data(max_minutes: int = _MAX_WAIT_MINUTES) -> bool:
    """Yahoo Finance에 오늘 종가가 반영될 때까지 최대 max_minutes분 대기.
    True: 오늘 데이터 확인됨, False: 타임아웃(그냥 실행)."""
    today = datetime.now(KST).date()
    deadline = datetime.now(KST).timestamp() + max_minutes * 60
    attempt = 0
    while True:
        attempt += 1
        try:
            hist = yf.Ticker("^KS11").history(period="5d")
            if not hist.empty:
                last = hist.index[-1]
                if hasattr(last, "tzinfo") and last.tzinfo:
                    last_date = last.astimezone(KST).date()
                else:
                    last_date = last.date()
                if last_date == today:
                    print(f"[국장 리포트] 오늘 종가 확인됨 (시도 {attempt}회)")
                    return True
                print(f"[국장 리포트] 최신 날짜={last_date}, 오늘={today} → {_RETRY_INTERVAL_SEC//60}분 후 재시도 ({attempt}회)")
        except Exception as e:
            print(f"[국장 리포트] 데이터 확인 실패: {e}")
        if datetime.now(KST).timestamp() >= deadline:
            print(f"[국장 리포트] {max_minutes}분 초과 — 현재 데이터로 그냥 실행")
            return False
        import time
        time.sleep(_RETRY_INTERVAL_SEC)


def fmt_krw(val: float) -> str:
    return f"{val:,.0f}원"


def load_watchlist_kr() -> dict:
    """워치리스트에서 한국 종목만 추출 (ticker: name)"""
    if not WATCHLIST_PATH.exists():
        return {}
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        wl = json.load(f)["stocks"]
    return {
        s["ticker"]: s.get("name", s["ticker"])
        for s in wl
        if s["ticker"].endswith(".KS") or s["ticker"].endswith(".KQ")
    }


async def run():
    from yahoo_finance import is_korean_market_open
    loop = asyncio.get_running_loop()
    # 15:30 마감 직후에는 Yahoo Finance 데이터가 미갱신일 수 있으므로 오늘 종가가 나올 때까지 대기
    await loop.run_in_executor(None, wait_for_today_data)

    if not is_korean_market_open():
        print(f"[국장 리포트] 오늘은 한국 장 휴장일 — 스킵 ({datetime.now().strftime('%Y-%m-%d')})")
        return

    print(f"[국장 리포트] 실행 시작: {datetime.now()}")
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. 지수 수집
    index_lines = []
    for ticker, name in KR_INDICES.items():
        data = await loop.run_in_executor(None, get_index_data, ticker)
        if data:
            arrow = "📈" if data["change"] >= 0 else "📉"
            dot = "🟢" if data["change"] >= 0 else "🔴"
            index_lines.append(f"{arrow} **{name}** {data['current']:,.2f} {dot} {data['change']:+.2f}%")

    # 2. KOSPI 시총 상위 20 (실시간)
    kospi_top = await loop.run_in_executor(None, fetch_kospi_top, KOSPI_TOP_N)

    # 3. 워치리스트 한국 종목
    watchlist_kr = load_watchlist_kr()

    # 4. 합치기 (중복 제거 — 워치리스트 이름 우선)
    target_stocks = {**kospi_top}
    for ticker, name in watchlist_kr.items():
        target_stocks[ticker] = name  # 워치리스트 종목은 이름 덮어쓰기

    watchlist_tickers = set(watchlist_kr.keys())

    # 5. 종목 데이터 수집
    stock_results = []
    for ticker, name in target_stocks.items():
        data = await loop.run_in_executor(None, get_stock_data, ticker)
        if data:
            stock_results.append({
                "ticker": ticker,
                "name": name,
                "is_watchlist": ticker in watchlist_tickers,
                **data,
            })

    stock_results.sort(key=lambda x: x["change"], reverse=True)

    # 6. Discord 표시 — 워치리스트 종목은 ⭐ 표시
    kospi_lines = []
    watchlist_lines = []
    for s in stock_results:
        dot = "🟢" if s["change"] >= 0 else "🔴"
        line = f"{dot} **{s['name']}** {fmt_krw(s['current'])} ({s['change']:+.2f}%)"
        if s["is_watchlist"] and s["ticker"] not in [t for t in kospi_top]:
            watchlist_lines.append(f"⭐ {line}")
        else:
            star = " ⭐" if s["is_watchlist"] else ""
            kospi_lines.append(f"{line}{star}")

    fields = [
        {
            "name": "📊 주요 지수",
            "value": "\n".join(index_lines) if index_lines else "데이터 없음",
            "inline": False,
        },
        {
            "name": f"🏆 KOSPI 시총 상위 {KOSPI_TOP_N} (실시간)",
            "value": "\n".join(kospi_lines[:20]) if kospi_lines else "데이터 없음",
            "inline": False,
        },
    ]

    if watchlist_lines:
        fields.append({
            "name": f"⭐ 워치리스트 추가 종목 ({len(watchlist_lines)}개)",
            "value": "\n".join(watchlist_lines),
            "inline": False,
        })

    embed = {
        "title": f"🇰🇷 국장 마감 리포트 — {today}",
        "color": 0x3fb950,
        "fields": fields,
        "footer": {"text": f"KOSPI 시총 상위 {KOSPI_TOP_N} (실시간) + 워치리스트 | Yahoo Finance / FinanceDataReader"},
        "timestamp": datetime.now().isoformat(),
    }
    await send_embed(CH_DAILY_SUMMARY, embed)

    print(f"[국장 리포트] 완료: KOSPI 상위 {len(kospi_top)}개 + 워치리스트 {len(watchlist_lines)}개")

    # 7. 한국 시장 지표 (코스피·코스닥 지수 + 등락 종목수)
    from market_indicators import run_korea as run_indicators_korea
    await run_indicators_korea()


if __name__ == "__main__":
    asyncio.run(run())
