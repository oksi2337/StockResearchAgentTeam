"""
run_daily.py — 장 마감 후 일괄 실행 스크립트
Windows Task Scheduler에 등록해서 매일 오전 7시(미장 마감 후)에 실행
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    from market_watcher import run as run_watcher
    from sector_analyst import run as run_sector

    print("=" * 50)
    print("일간 리서치 에이전트 팀 시작")
    print("=" * 50)

    await run_watcher()
    await asyncio.sleep(2)

    await run_sector()

    print("=" * 50)
    print("일간 리서치 완료")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
