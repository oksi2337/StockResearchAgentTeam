"""
Market Watcher — 매일 장 마감 후 실행
Top 20 시총 + 워치리스트 감시, 순위 변동 감지, Discord 전송
"""
import os
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

DATA_DIR = Path(__file__).parent.parent / "data"
WATCHLIST_PATH = DATA_DIR / "watchlist.json"
INDEX_PATH = DATA_DIR / "index.json"

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CH_MARKET_ALERT = int(os.getenv("DISCORD_CH_MARKET_ALERT"))
CH_DAILY_SUMMARY = int(os.getenv("DISCORD_CH_DAILY_SUMMARY"))

DISCORD_API = "https://discord.com/api/v10"


async def send_discord_message(channel_id: int, content: str = None, embeds: list = None):
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"}
    payload = {}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            headers=headers,
            json=payload,
        ) as resp:
            if resp.status not in (200, 201):
                print(f"[Discord] 전송 실패: {resp.status} {await resp.text()}")


def load_latest_data() -> dict | None:
    if not INDEX_PATH.exists():
        return None
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index = json.load(f)
    if not index.get("dates"):
        return None
    latest_date = sorted(index["dates"])[-1]
    data_file = DATA_DIR / f"marketcap-{latest_date}.json"
    if not data_file.exists():
        return None
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_prev_data(skip: int = 1) -> dict | None:
    if not INDEX_PATH.exists():
        return None
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index = json.load(f)
    dates = sorted(index.get("dates", []))
    if len(dates) < skip + 1:
        return None
    target_date = dates[-(skip + 1)]
    data_file = DATA_DIR / f"marketcap-{target_date}.json"
    if not data_file.exists():
        return None
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_rank_changes(current: dict, previous: dict) -> list:
    """Top 10 순위 변동 감지"""
    if not current or not previous:
        return []

    curr_top = {e["ticker"]: e["rank"] for e in current["data"][:20]}
    prev_top = {e["ticker"]: e["rank"] for e in previous["data"][:20]}

    changes = []
    for entry in current["data"][:10]:
        ticker = entry["ticker"]
        curr_rank = entry["rank"]
        prev_rank = prev_top.get(ticker)

        if prev_rank is None:
            changes.append({"ticker": ticker, "name": entry["name"], "curr_rank": curr_rank, "prev_rank": None, "type": "신규진입"})
        elif abs(curr_rank - prev_rank) >= 2:
            changes.append({
                "ticker": ticker,
                "name": entry["name"],
                "curr_rank": curr_rank,
                "prev_rank": prev_rank,
                "diff": prev_rank - curr_rank,
                "type": "상승" if curr_rank < prev_rank else "하락",
            })
    return changes


def fmt_usd(val: float) -> str:
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    return f"${val/1e6:.0f}M"


async def send_daily_summary(data: dict, rank_changes: list):
    today = data["date"]
    top20 = data["data"][:20]

    # 일간 요약 embed
    lines = []
    for e in top20:
        arrow = "🟢" if e.get("change_1d_pct", 0) >= 0 else "🔴"
        change = e.get("change_1d_pct", 0)
        lines.append(f"`{e['rank']:2d}.` **{e['name']}** ({e['ticker']}) {fmt_usd(e['market_cap_usd'])} {arrow} {change:+.1f}%")

    summary_embed = {
        "title": f"📊 일간 시총 Top 20 요약 — {today}",
        "description": "\n".join(lines[:20]),
        "color": 0x3fb950,
        "footer": {"text": f"환율: {data.get('rate', 'N/A')} KRW/USD"},
        "timestamp": datetime.now().isoformat(),
    }
    await send_discord_message(CH_DAILY_SUMMARY, embeds=[summary_embed])

    # 순위 변동 알림
    if rank_changes:
        alert_lines = []
        for c in rank_changes:
            if c["type"] == "신규진입":
                alert_lines.append(f"🆕 **{c['name']}** Top 10 신규 진입 (현재 {c['curr_rank']}위)")
            else:
                emoji = "⬆️" if c["type"] == "상승" else "⬇️"
                alert_lines.append(f"{emoji} **{c['name']}** {c['prev_rank']}위 → {c['curr_rank']}위 ({c['diff']:+d})")

        alert_embed = {
            "title": "🚨 Top 10 순위 변동 감지",
            "description": "\n".join(alert_lines),
            "color": 0xf0e040,
            "timestamp": datetime.now().isoformat(),
        }
        await send_discord_message(CH_MARKET_ALERT, embeds=[alert_embed])


async def check_watchlist_alerts(data: dict):
    """워치리스트 종목 급변 감지"""
    if not WATCHLIST_PATH.exists():
        return

    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        watchlist = json.load(f)["stocks"]

    if not watchlist:
        return

    from yahoo_finance import check_alerts
    import sys
    sys.path.insert(0, str(Path(__file__).parent))

    alerts = []
    for stock in watchlist:
        alert = check_alerts(stock["ticker"], threshold_pct=5.0)
        if alert:
            alerts.append(alert)

    if alerts:
        lines = []
        for a in alerts:
            emoji = "🚀" if a["alert"] == "급등" else "💥"
            lines.append(f"{emoji} **{a['ticker']}** {a['change_pct']:+.2f}% ({a['alert']}) — ${a['current_price']:,.2f}")

        embed = {
            "title": "⚠️ 워치리스트 급변 감지",
            "description": "\n".join(lines),
            "color": 0xff6b35,
            "timestamp": datetime.now().isoformat(),
        }
        await send_discord_message(CH_MARKET_ALERT, embeds=[embed])


async def run():
    print(f"[Market Watcher] 실행 시작: {datetime.now()}")

    current = load_latest_data()
    if not current:
        print("[Market Watcher] 수집된 데이터 없음. 대시보드에서 먼저 데이터를 수집하세요.")
        return

    previous = load_prev_data()
    rank_changes = detect_rank_changes(current, previous)

    await send_daily_summary(current, rank_changes)
    await check_watchlist_alerts(current)

    print(f"[Market Watcher] 완료: 순위변동 {len(rank_changes)}건")


if __name__ == "__main__":
    asyncio.run(run())
