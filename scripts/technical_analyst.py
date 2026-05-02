"""
Technical Analyst — 워치리스트 + Top 20 기술적 분석
매일 장 마감 후 실행, 결과를 #종목-분석 채널에 전송
"""
from __future__ import annotations
import os
import json
import asyncio
import aiohttp
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from yahoo_finance import get_technical_indicators, get_fundamentals

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CH_STOCK_ANALYSIS = int(os.getenv("DISCORD_CH_STOCK_ANALYSIS"))
WATCHLIST_PATH = Path(__file__).parent.parent / "data" / "watchlist.json"
DATA_DIR = Path(__file__).parent.parent / "data"

DISCORD_API = "https://discord.com/api/v10"


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


def build_tech_embed(tech: dict, fund: dict | None) -> dict:
    direction = "📈" if tech["change_pct"] >= 0 else "📉"
    color = 0x3fb950 if tech["change_pct"] >= 0 else 0xf85149
    name = fund["name"] if fund else tech["ticker"]

    rsi_label = "🔴 과매수" if tech["rsi"] > 70 else "🔵 과매도" if tech["rsi"] < 30 else "⚪ 중립"
    macd_label = "🟢 골든크로스" if tech["macd_hist"] > 0 else "🔴 데드크로스"

    ma_txt = f"MA20: ${tech['ma20']:,.2f}"
    if tech["ma50"]:
        ma_txt += f"\nMA50: ${tech['ma50']:,.2f}"
    if tech["ma200"]:
        ma_txt += f"\nMA200: ${tech['ma200']:,.2f}"

    fields = [
        {"name": "💰 현재가", "value": f"${tech['current_price']:,.2f} ({tech['change_pct']:+.2f}%)", "inline": True},
        {"name": "📊 RSI(14)", "value": f"{tech['rsi']:.1f} — {rsi_label}", "inline": True},
        {"name": "⚡ MACD", "value": f"{macd_label}\nHist: {tech['macd_hist']:+.4f}", "inline": True},
        {"name": "📏 이동평균", "value": ma_txt, "inline": True},
        {"name": "📐 52주 범위", "value": f"고가: ${tech['week52_high']:,.2f} ({tech['price_vs_52h']:+.1f}%)\n저가: ${tech['week52_low']:,.2f} ({tech['price_vs_52l']:+.1f}%)", "inline": True},
        {"name": "📦 거래량", "value": f"{tech['volume']:,}\n(평균 대비 {tech['volume_ratio']:.1f}x)" if tech["volume_ratio"] else f"{tech['volume']:,}", "inline": True},
    ]

    if fund:
        pe = f"{fund['pe_ratio']:.1f}" if fund.get("pe_ratio") else "N/A"
        pb = f"{fund['pb_ratio']:.2f}" if fund.get("pb_ratio") else "N/A"
        rec = fund.get("recommendation", "N/A").upper()
        target = f"${fund['analyst_target']:,.2f}" if fund.get("analyst_target") else "N/A"
        fields.append({
            "name": "📋 밸류에이션",
            "value": f"PER: {pe} | PBR: {pb}\n애널리스트 목표가: {target} | 추천: {rec}",
            "inline": False,
        })

    return {
        "title": f"{direction} {name} ({tech['ticker']}) 기술적 분석",
        "color": color,
        "fields": fields,
        "footer": {"text": "데이터: Yahoo Finance"},
        "timestamp": datetime.now().isoformat(),
    }


async def analyze_ticker(ticker: str):
    print(f"[Technical Analyst] 분석 중: {ticker}")
    tech = await asyncio.get_event_loop().run_in_executor(None, get_technical_indicators, ticker)
    fund = await asyncio.get_event_loop().run_in_executor(None, get_fundamentals, ticker)

    if tech:
        embed = build_tech_embed(tech, fund)
        await send_embed(CH_STOCK_ANALYSIS, embed)
    else:
        print(f"[Technical Analyst] {ticker} 데이터 없음")


async def run(tickers: list[str] | None = None):
    print(f"[Technical Analyst] 실행 시작: {datetime.now()}")

    if tickers is None:
        # 워치리스트 로드
        tickers = []
        if WATCHLIST_PATH.exists():
            with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
                watchlist = json.load(f)["stocks"]
            tickers = [s["ticker"] for s in watchlist]

        # Top 20에서 미국 주식 티커 추가
        index_path = DATA_DIR / "index.json"
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                index = json.load(f)
            if index.get("dates"):
                latest = sorted(index["dates"])[-1]
                data_file = DATA_DIR / f"marketcap-{latest}.json"
                if data_file.exists():
                    with open(data_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    top20_tickers = [e["ticker"] for e in data["data"][:20] if e.get("ticker")]
                    for t in top20_tickers:
                        if t not in tickers:
                            tickers.append(t)

    if not tickers:
        print("[Technical Analyst] 분석할 종목 없음")
        return

    # 헤더 메시지
    header_embed = {
        "title": f"🔬 기술적 분석 리포트 — {datetime.now().strftime('%Y-%m-%d')}",
        "description": f"분석 종목 {len(tickers)}개: {', '.join(tickers)}",
        "color": 0x5865f2,
        "timestamp": datetime.now().isoformat(),
    }
    await send_embed(CH_STOCK_ANALYSIS, header_embed)

    # 종목별 분석 (API 과부하 방지 위해 순차 실행)
    for ticker in tickers:
        await analyze_ticker(ticker)
        await asyncio.sleep(1)

    print(f"[Technical Analyst] 완료: {len(tickers)}개 분석")


if __name__ == "__main__":
    import sys
    tickers_arg = sys.argv[1:] if len(sys.argv) > 1 else None
    asyncio.run(run(tickers_arg))
