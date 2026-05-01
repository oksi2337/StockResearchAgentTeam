"""
Deep Analyst — stock-agent 방식의 심층 분석
Claude API + web_search로 7단계 리서치 수행 후 Discord #종목-분석 채널에 전송
"""
import os
import json
import asyncio
import aiohttp
import anthropic
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CH_STOCK_ANALYSIS = int(os.getenv("DISCORD_CH_STOCK_ANALYSIS"))

DISCORD_API = "https://discord.com/api/v10"

SYSTEM_PROMPT = """당신은 주식 리서치 전문 애널리스트입니다.
요청된 기업에 대해 웹 검색을 활용해 다음 7개 항목을 조사하고, 반드시 아래 JSON 형식으로만 응답하세요.
다른 설명 없이 순수 JSON만 출력하세요.

{
  "company": "기업명",
  "ticker": "티커",
  "date": "YYYY-MM-DD",
  "weekly_performance": "주간 등락률 및 현재가",
  "price_driver": "주가 변동 핵심 사유",
  "competitive_advantage": "경쟁 우위 및 해자 요약",
  "valuation": "포워드 PER / EV EBITDA 추정",
  "fundamentals": "최근 실적 및 펀더멘털 변화",
  "outlook": "향후 성장 전망 및 리스크",
  "analyst_ratings": ["증권사A: Buy $XXX", "증권사B: Hold $XXX"],
  "news": [
    {"title": "뉴스 제목", "summary": "1~2문장 요약"}
  ]
}"""


async def send_message(channel_id: int, content: str = None, embed: dict = None):
    headers = {"Authorization": f"Bot {DISCORD_TOKEN}", "Content-Type": "application/json"}
    payload = {}
    if content:
        payload["content"] = content
    if embed:
        payload["embeds"] = [embed]
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            headers=headers,
            json=payload,
        ) as resp:
            if resp.status not in (200, 201):
                print(f"[Discord] 전송 실패: {resp.status} {await resp.text()}")


def run_research(company: str, ticker: str) -> dict | None:
    """Claude API로 심층 리서치 실행"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    messages = [
        {
            "role": "user",
            "content": f"다음 기업을 분석해주세요: {company} ({ticker})\n\n"
                       f"검색 키워드 예시:\n"
                       f"- {ticker} stock price performance this week\n"
                       f"- {company} earnings revenue latest quarter 2026\n"
                       f"- {company} analyst rating price target 2026\n"
                       f"- {company} competitive advantage market share\n"
                       f"- {company} business outlook forecast 2026 2027\n"
                       f"- {company} news this week 2026\n"
                       f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}",
        }
    ]

    print(f"[Deep Analyst] {company} ({ticker}) 리서치 시작...")
    full_text = ""

    with client.messages.stream(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=messages,
    ) as stream:
        for event in stream:
            if hasattr(event, "type"):
                if event.type == "content_block_start":
                    if hasattr(event.content_block, "type"):
                        if event.content_block.type == "tool_use":
                            if hasattr(event.content_block, "input"):
                                query = event.content_block.input.get("query", "")
                                print(f"[Deep Analyst] 검색 중: {query}")
                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        full_text += event.delta.text

    # JSON 추출
    try:
        start = full_text.find("{")
        end = full_text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(full_text[start:end])
    except Exception as e:
        print(f"[Deep Analyst] JSON 파싱 실패: {e}")
        print(f"원본 응답: {full_text[:500]}")
    return None


def build_embeds(data: dict) -> list:
    """Discord embed 목록 생성"""
    color = 0x5865f2
    now = datetime.now().isoformat()
    company = data.get("company", "")
    ticker = data.get("ticker", "")

    # 메인 분석 embed
    main_embed = {
        "title": f"🔬 {company} ({ticker}) 심층 분석",
        "color": color,
        "fields": [
            {
                "name": "📈 주간 성과",
                "value": data.get("weekly_performance", "N/A") or "N/A",
                "inline": False,
            },
            {
                "name": "⚡ 주가 변동 사유",
                "value": (data.get("price_driver", "N/A") or "N/A")[:1024],
                "inline": False,
            },
            {
                "name": "🏆 경쟁 우위",
                "value": (data.get("competitive_advantage", "N/A") or "N/A")[:1024],
                "inline": False,
            },
            {
                "name": "💰 밸류에이션",
                "value": (data.get("valuation", "N/A") or "N/A")[:1024],
                "inline": True,
            },
            {
                "name": "📊 펀더멘털",
                "value": (data.get("fundamentals", "N/A") or "N/A")[:1024],
                "inline": True,
            },
            {
                "name": "🔭 향후 전망",
                "value": (data.get("outlook", "N/A") or "N/A")[:1024],
                "inline": False,
            },
        ],
        "footer": {"text": "데이터: Claude + Web Search"},
        "timestamp": now,
    }

    embeds = [main_embed]

    # 증권사 의견 embed
    ratings = data.get("analyst_ratings", [])
    if ratings:
        ratings_embed = {
            "title": f"📋 {ticker} 증권사 의견",
            "color": 0xf0e040,
            "description": "\n".join(f"• {r}" for r in ratings[:10]),
            "timestamp": now,
        }
        embeds.append(ratings_embed)

    # 뉴스 embed
    news = data.get("news", [])
    if news:
        news_lines = []
        for item in news[:8]:
            title = item.get("title", "")
            summary = item.get("summary", "")
            news_lines.append(f"**{title}**\n{summary}")
        news_embed = {
            "title": f"📰 {ticker} 주요 뉴스",
            "color": 0x3fb950,
            "description": "\n\n".join(news_lines)[:4096],
            "timestamp": now,
        }
        embeds.append(news_embed)

    return embeds


async def analyze(company: str, ticker: str):
    """심층 분석 실행 및 Discord 전송"""
    await send_message(CH_STOCK_ANALYSIS, content=f"🔍 **{company} ({ticker})** 심층 분석 시작... (1~2분 소요)")

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, run_research, company, ticker)

    if not data:
        await send_message(CH_STOCK_ANALYSIS, content=f"❌ {ticker} 분석 실패 — 잠시 후 다시 시도해주세요.")
        return

    embeds = build_embeds(data)
    for embed in embeds:
        await send_message(CH_STOCK_ANALYSIS, embed=embed)

    print(f"[Deep Analyst] {ticker} 완료")


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        asyncio.run(analyze(sys.argv[1], sys.argv[2]))
    else:
        print("사용법: python deep_analyst.py [기업명] [티커]")
        print("예시: python deep_analyst.py NVIDIA NVDA")
