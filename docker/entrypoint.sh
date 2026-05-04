#!/bin/bash
set -e

mkdir -p /app/logs

# cron 환경에서도 .env를 직접 읽으므로 별도 env 전달 불필요
# (모든 Python 스크립트가 load_dotenv()로 /app/.env를 로드)

# crontab 등록
crontab /app/docker/crontab
echo "[$(date '+%Y-%m-%d %H:%M:%S')] cron 등록 완료"

# cron 데몬 시작
cron
echo "[$(date '+%Y-%m-%d %H:%M:%S')] cron 데몬 시작"

# Discord 봇 포그라운드 실행 (컨테이너를 살아있게 유지)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Discord 봇 시작..."
exec python -u scripts/discord_bot.py
