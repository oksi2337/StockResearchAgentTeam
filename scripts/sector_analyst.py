"""
Sector Analyst — 매일 장 마감 후 실행
섹터별 시총 집계, 자금 흐름, 섹터 로테이션 분석 → #섹터-동향 전송
"""
from __future__ import annotations
import os
import json
import asyncio
import aiohttp
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CH_SECTOR_TREND = int(os.getenv("DISCORD_CH_SECTOR_TREND"))
DATA_DIR = Path(__file__).parent.parent / "data"

DISCORD_API = "https://discord.com/api/v10"

SECTOR_EMOJI = {
    "Technology": "💻",
    "Finance": "🏦",
    "Healthcare": "🏥",
    "Energy": "⚡",
    "Consumer": "🛍️",
    "Industrial": "🏭",
    "Other": "🔷",
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


def fmt_usd(val: float) -> str:
    if val >= 1e12:
        return f"${val/1e12:.2f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    return f"${val/1e6:.0f}M"


def aggregate_sectors(data: dict) -> dict:
    sectors = defaultdict(lambda: {"total_cap": 0, "count": 0, "avg_change": 0, "changes": []})
    for entry in data["data"]:
        sector = entry.get("sector", "Other")
        cap = entry.get("market_cap_usd", 0)
        change = entry.get("change_1d_pct", 0)
        sectors[sector]["total_cap"] += cap
        sectors[sector]["count"] += 1
        sectors[sector]["changes"].append(change)

    for s in sectors.values():
        if s["changes"]:
            s["avg_change"] = sum(s["changes"]) / len(s["changes"])
        del s["changes"]

    return dict(sorted(sectors.items(), key=lambda x: x[1]["total_cap"], reverse=True))


def compare_sector_flows(current_sectors: dict, prev_sectors: dict) -> dict:
    """섹터별 시총 변화 (자금 흐름)"""
    flows = {}
    for sector, curr in current_sectors.items():
        prev = prev_sectors.get(sector, {"total_cap": 0})
        cap_change = curr["total_cap"] - prev["total_cap"]
        cap_change_pct = cap_change / prev["total_cap"] * 100 if prev["total_cap"] else 0
        flows[sector] = {
            **curr,
            "cap_change": cap_change,
            "cap_change_pct": cap_change_pct,
        }
    return flows


def load_data(date_offset: int = 0) -> dict | None:
    index_path = DATA_DIR / "index.json"
    if not index_path.exists():
        return None
    with open(index_path, "r", encoding="utf-8") as f:
        index = json.load(f)
    dates = sorted(index.get("dates", []))
    if len(dates) <= date_offset:
        return None
    target = dates[-(date_offset + 1)]
    data_file = DATA_DIR / f"marketcap-{target}.json"
    if not data_file.exists():
        return None
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)


async def run():
    print(f"[Sector Analyst] 실행 시작: {datetime.now()}")

    current = load_data(0)
    if not current:
        print("[Sector Analyst] 데이터 없음")
        return

    previous = load_data(1)

    curr_sectors = aggregate_sectors(current)

    if previous:
        prev_sectors = aggregate_sectors(previous)
        flows = compare_sector_flows(curr_sectors, prev_sectors)
    else:
        flows = {s: {**v, "cap_change": 0, "cap_change_pct": 0} for s, v in curr_sectors.items()}

    total_cap = sum(v["total_cap"] for v in curr_sectors.values())

    lines = []
    for sector, data in flows.items():
        emoji = SECTOR_EMOJI.get(sector, "🔷")
        share = data["total_cap"] / total_cap * 100 if total_cap else 0
        flow_arrow = "▲" if data["cap_change_pct"] > 0 else "▼" if data["cap_change_pct"] < 0 else "─"
        flow_color = "🟢" if data["cap_change_pct"] > 0 else "🔴" if data["cap_change_pct"] < 0 else "⚪"
        lines.append(
            f"{emoji} **{sector}** — {fmt_usd(data['total_cap'])} ({share:.1f}%)\n"
            f"  {flow_color} 자금흐름: {flow_arrow}{abs(data['cap_change_pct']):.2f}% | "
            f"평균 등락: {data['avg_change']:+.2f}% | {data['count']}개 기업"
        )

    # 최강/최약 섹터
    best = max(flows.items(), key=lambda x: x[1]["avg_change"])
    worst = min(flows.items(), key=lambda x: x[1]["avg_change"])

    embed = {
        "title": f"🏭 섹터 동향 분석 — {current['date']}",
        "description": "\n\n".join(lines),
        "color": 0x5865f2,
        "fields": [
            {
                "name": "🏆 강세 섹터",
                "value": f"{SECTOR_EMOJI.get(best[0], '🔷')} **{best[0]}** — 평균 {best[1]['avg_change']:+.2f}%",
                "inline": True,
            },
            {
                "name": "💔 약세 섹터",
                "value": f"{SECTOR_EMOJI.get(worst[0], '🔷')} **{worst[0]}** — 평균 {worst[1]['avg_change']:+.2f}%",
                "inline": True,
            },
            {
                "name": "💰 전체 시총",
                "value": fmt_usd(total_cap),
                "inline": True,
            },
        ],
        "footer": {"text": f"Top {len(current['data'])}개 기업 기준"},
        "timestamp": datetime.now().isoformat(),
    }

    await send_embed(CH_SECTOR_TREND, embed)
    print(f"[Sector Analyst] 완료: {len(curr_sectors)}개 섹터 분석")


if __name__ == "__main__":
    asyncio.run(run())
