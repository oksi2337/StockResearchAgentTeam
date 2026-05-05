"""
run_daily.py — 장 마감 후 일괄 실행 스크립트
매일 오전 7시(미장 마감 후)에 실행. NAS Docker cron 및 Windows Task Scheduler 모두 지원.
실행 순서: 시총 수집(yfinance) → 글로벌 지표 → 시장 감시 → 섹터 분석
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    from collect_marketcap_live import collect_and_save
    from market_watcher import run as run_watcher
    from sector_analyst import run as run_sector
    from market_indicators import run_global as run_indicators_global

    print("=" * 50)
    print("일간 리서치 에이전트 팀 시작")
    print("=" * 50)

    # 1. 시총 데이터 수집 (NAS에서도 독립 실행 — data/ 파일 불필요)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, collect_and_save)
    await asyncio.sleep(2)

    await run_indicators_global()
    await asyncio.sleep(2)

    await run_watcher()
    await asyncio.sleep(2)

    await run_sector()

    print("=" * 50)
    print("일간 리서치 완료")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
