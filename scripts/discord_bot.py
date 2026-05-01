import discord
from discord.ext import commands
import os
import json
import asyncio
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
CH_MARKET_ALERT = int(os.getenv("DISCORD_CH_MARKET_ALERT"))
CH_DAILY_SUMMARY = int(os.getenv("DISCORD_CH_DAILY_SUMMARY"))
CH_STOCK_ANALYSIS = int(os.getenv("DISCORD_CH_STOCK_ANALYSIS"))
CH_SECTOR_TREND = int(os.getenv("DISCORD_CH_SECTOR_TREND"))

WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "watchlist.json")
BASE_DIR = os.path.join(os.path.dirname(__file__), "..")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ── 워치리스트 유틸 ──────────────────────────────────────────
def load_watchlist() -> list:
    with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["stocks"]


def save_watchlist(stocks: list):
    with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
        json.dump({"stocks": stocks, "updated_at": datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)


# ── 봇 이벤트 ───────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[봇 시작] {bot.user} 로그인 완료")
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"[슬래시 커맨드] {len(synced)}개 동기화 완료")
    except Exception as e:
        print(f"[슬래시 커맨드] 동기화 실패: {e}")


# ── 자연어 메시지 처리 ───────────────────────────────────────
@bot.event
async def on_message(message: discord.Message):
    print(f"[메시지 수신] {message.author}: {repr(message.content)}")
    if message.author.bot:
        return

    content = message.content.strip()

    # 티커 추출 — 미국(AAPL), 한국(005930.KS / 009150.KQ) 모두 지원
    def extract_tickers(text: str) -> list[str]:
        import re
        text = text.upper()
        # 한국 티커: 숫자6자리.KS 또는 .KQ
        kr = re.findall(r'\b\d{6}\.(KS|KQ)\b', text)
        kr_tickers = [m[0] and f"{text[text.index(m[0])-7:text.index(m[0])+3]}" for m in kr]
        kr_tickers = re.findall(r'\b\d{6}\.(?:KS|KQ)\b', text)
        # 미국 티커: 영문 1~5자
        us_tickers = re.findall(r'\b[A-Z]{1,5}\b', text)
        stopwords = {"추가", "해줘", "삭제", "빼줘", "제거", "분석", "목록", "KS", "KQ"}
        us_tickers = [t for t in us_tickers if t not in stopwords]
        return kr_tickers + us_tickers

    # 워치리스트 추가: "추가 AAPL", "005930.KS 추가해줘"
    if "추가" in content:
        tickers = extract_tickers(content.replace("추가", "").replace("해줘", ""))
        if tickers:
            stocks = load_watchlist()
            added = []
            for t in tickers:
                if t not in [s["ticker"] for s in stocks]:
                    stocks.append({"ticker": t, "added_at": datetime.now().isoformat()})
                    added.append(t)
            save_watchlist(stocks)
            if added:
                await message.reply(f"✅ 워치리스트에 추가됨: **{', '.join(added)}**")
            else:
                await message.reply("이미 워치리스트에 있는 종목이에요.")
            return

    # 워치리스트 제거: "삭제 AAPL", "005930.KS 빼줘"
    if "삭제" in content or "빼줘" in content or "제거" in content:
        tickers = extract_tickers(content.replace("삭제", "").replace("빼줘", "").replace("제거", ""))
        if tickers:
            stocks = load_watchlist()
            removed = [t for t in tickers if t in [s["ticker"] for s in stocks]]
            stocks = [s for s in stocks if s["ticker"] not in tickers]
            save_watchlist(stocks)
            if removed:
                await message.reply(f"🗑️ 워치리스트에서 제거됨: **{', '.join(removed)}**")
            else:
                await message.reply("워치리스트에 없는 종목이에요.")
            return

    # 워치리스트 조회: "목록", "워치리스트"
    if "목록" in content or "워치리스트" in content:
        stocks = load_watchlist()
        if stocks:
            ticker_list = "\n".join([f"• {s.get('name', s['ticker'])} ({s['ticker']})" for s in stocks])
            await message.reply(f"**📋 현재 워치리스트**\n{ticker_list}")
        else:
            await message.reply("워치리스트가 비어있어요. '추가 [티커]'로 종목을 추가하세요.")
        return

    # 개별 종목 분석: "분석 AAPL", "005930.KS 분석해줘"
    if "분석" in content:
        tickers = extract_tickers(content.replace("분석", "").replace("해줘", ""))
        if tickers:
            ticker = tickers[0]
            await message.reply(f"🔍 **{ticker}** 분석 시작합니다... (잠시 후 #종목-분석 채널에 결과가 올라와요)")
            asyncio.create_task(run_stock_analysis(ticker, message.channel))
            return

    await bot.process_commands(message)


async def run_stock_analysis(ticker: str, reply_channel):
    """기술적 분석 실행 후 Discord에 전송"""
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: __import__("yahoo_finance", fromlist=["get_technical_indicators", "get_fundamentals"]),
        )
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from yahoo_finance import get_technical_indicators, get_fundamentals

        tech = get_technical_indicators(ticker)
        fund = get_fundamentals(ticker)

        channel = bot.get_channel(CH_STOCK_ANALYSIS)
        if channel and tech:
            embed = build_analysis_embed(ticker, tech, fund)
            await channel.send(embed=embed)
    except Exception as e:
        await reply_channel.send(f"❌ {ticker} 분석 중 오류: {e}")


def build_analysis_embed(ticker: str, tech: dict, fund: dict) -> discord.Embed:
    direction = "📈" if tech["change_pct"] >= 0 else "📉"
    color = discord.Color.green() if tech["change_pct"] >= 0 else discord.Color.red()
    name = fund["name"] if fund else ticker

    embed = discord.Embed(
        title=f"{direction} {name} ({ticker}) 분석",
        color=color,
        timestamp=datetime.now(),
    )

    embed.add_field(
        name="💰 가격",
        value=f"${tech['current_price']:,.2f} ({tech['change_pct']:+.2f}%)",
        inline=True,
    )
    embed.add_field(
        name="📊 RSI",
        value=f"{tech['rsi']:.1f} {'🔴과매수' if tech['rsi'] > 70 else '🔵과매도' if tech['rsi'] < 30 else '⚪중립'}",
        inline=True,
    )
    embed.add_field(
        name="⚡ MACD",
        value=f"{'🟢' if tech['macd_hist'] > 0 else '🔴'} {tech['macd_hist']:+.4f}",
        inline=True,
    )
    embed.add_field(
        name="📏 이동평균",
        value=f"MA20: ${tech['ma20']:,.2f}\nMA50: ${tech['ma50']:,.2f}" if tech['ma50'] else f"MA20: ${tech['ma20']:,.2f}",
        inline=True,
    )
    embed.add_field(
        name="📐 52주 범위",
        value=f"고가: ${tech['week52_high']:,.2f} ({tech['price_vs_52h']:+.1f}%)\n저가: ${tech['week52_low']:,.2f} ({tech['price_vs_52l']:+.1f}%)",
        inline=True,
    )
    embed.add_field(
        name="📦 거래량",
        value=f"{tech['volume']:,} (평균 대비 {tech['volume_ratio']:.1f}x)" if tech['volume_ratio'] else f"{tech['volume']:,}",
        inline=True,
    )

    if fund:
        pe = f"{fund['pe_ratio']:.1f}" if fund['pe_ratio'] else "N/A"
        pb = f"{fund['pb_ratio']:.2f}" if fund['pb_ratio'] else "N/A"
        embed.add_field(
            name="📋 밸류에이션",
            value=f"PER: {pe} | PBR: {pb}\n추천: {fund['recommendation'].upper()}",
            inline=False,
        )

    return embed


# ── 종목명 → 티커 변환 헬퍼 ─────────────────────────────────
import sys as _sys
_sys.path.insert(0, os.path.dirname(__file__))
from kr_stocks import resolve_ticker, find_ticker, is_korean


async def resolve_or_reply(interaction: discord.Interaction, input_str: str) -> tuple[str | None, str | None]:
    """
    종목명 또는 티커 입력을 (ticker, name)으로 변환.
    여러 후보가 있으면 Discord에 목록 표시 후 None 반환.
    """
    loop = asyncio.get_event_loop()
    ticker, name = await loop.run_in_executor(None, resolve_ticker, input_str)

    if ticker:
        return ticker, name or input_str

    if is_korean(input_str):
        candidates = await loop.run_in_executor(None, find_ticker, input_str)
        if not candidates:
            await interaction.followup.send(f"❌ **{input_str}** 종목을 찾을 수 없어요. 티커로 직접 입력해보세요. (예: `005930.KS`)")
            return None, None
        lines = "\n".join([f"• {c['name']} → `{c['ticker']}` ({c['market']})" for c in candidates])
        await interaction.followup.send(f"**'{input_str}'** 검색 결과:\n{lines}\n\n정확한 종목을 위 티커로 다시 입력해주세요.")
        return None, None

    return input_str.upper(), input_str.upper()


# ── 슬래시 커맨드 ────────────────────────────────────────────
guild_obj = discord.Object(id=GUILD_ID)


@bot.tree.command(guild=guild_obj, name="워치리스트", description="현재 워치리스트 조회")
async def slash_watchlist(interaction: discord.Interaction):
    stocks = load_watchlist()
    if stocks:
        ticker_list = "\n".join([f"• {s.get('name', s['ticker'])} (`{s['ticker']}`)" for s in stocks])
        await interaction.response.send_message(f"**📋 현재 워치리스트** ({len(stocks)}개)\n{ticker_list}")
    else:
        await interaction.response.send_message("워치리스트가 비어있어요.")


@bot.tree.command(guild=guild_obj, name="추가", description="워치리스트에 종목 추가 (종목명 또는 티커)")
async def slash_add(interaction: discord.Interaction, 종목: str):
    await interaction.response.defer()
    ticker, name = await resolve_or_reply(interaction, 종목)
    if not ticker:
        return
    stocks = load_watchlist()
    if ticker not in [s["ticker"] for s in stocks]:
        stocks.append({"ticker": ticker, "name": name or ticker, "added_at": datetime.now().isoformat()})
        save_watchlist(stocks)
        await interaction.followup.send(f"✅ **{name or ticker}** (`{ticker}`) 워치리스트에 추가됨")
    else:
        await interaction.followup.send(f"**{name or ticker}**은 이미 워치리스트에 있어요.")


@bot.tree.command(guild=guild_obj, name="삭제", description="워치리스트에서 종목 제거 (종목명 또는 티커)")
async def slash_remove(interaction: discord.Interaction, 종목: str):
    await interaction.response.defer()
    ticker, name = await resolve_or_reply(interaction, 종목)
    if not ticker:
        return
    stocks = load_watchlist()
    match = next((s for s in stocks if s["ticker"] == ticker), None)
    if match:
        stocks = [s for s in stocks if s["ticker"] != ticker]
        save_watchlist(stocks)
        await interaction.followup.send(f"🗑️ **{match.get('name', ticker)}** (`{ticker}`) 제거됨")
    else:
        await interaction.followup.send(f"**{ticker}**은 워치리스트에 없어요.")


@bot.tree.command(guild=guild_obj, name="분석", description="기술적 분석 (종목명 또는 티커, 빠름)")
async def slash_analyze(interaction: discord.Interaction, 종목: str):
    await interaction.response.defer()
    ticker, name = await resolve_or_reply(interaction, 종목)
    if not ticker:
        return
    await interaction.followup.send(f"📊 **{name or ticker}** (`{ticker}`) 기술적 분석 중... #종목-분석 채널을 확인하세요.")
    asyncio.create_task(run_stock_analysis(ticker, None))


@bot.tree.command(guild=guild_obj, name="심층분석", description="심층 분석 — 뉴스·펀더멘털·증권사 의견 포함 (1~2분, 종목명 또는 티커)")
async def slash_deep_analyze(interaction: discord.Interaction, 종목: str):
    await interaction.response.defer()
    ticker, name = await resolve_or_reply(interaction, 종목)
    if not ticker:
        return
    await interaction.followup.send(
        f"🔬 **{name or ticker}** (`{ticker}`) 심층 분석 시작합니다.\n"
        f"뉴스·펀더멘털·증권사 의견 포함 — 1~2분 후 #종목-분석 채널을 확인하세요."
    )
    from deep_analyst import analyze
    asyncio.create_task(analyze(name or ticker, ticker))


if __name__ == "__main__":
    bot.run(TOKEN)
