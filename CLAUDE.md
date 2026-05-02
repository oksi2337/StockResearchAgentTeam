# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Dashboard (Node.js)**
```bash
npm run dev              # 서버(3001) + 클라이언트(5173) 동시 실행
npm run dev:server      # Express 서버만 (tsx watch)
npm run dev:client      # Vite 개발 서버만
npm run build           # tsc 서버 컴파일 + Vite 클라이언트 빌드
```

**Discord Agent Team (Python)**
```bash
python scripts/discord_bot.py                      # Discord 봇 실행 (수동)
python scripts/run_daily.py                        # 미장 마감 후 전체 리포트 일괄 실행
python scripts/korean_market_report.py             # 국장 마감 리포트 단독 실행
python scripts/technical_analyst.py AAPL TSLA      # 특정 종목 기술적 분석
python scripts/deep_analyst.py "NVIDIA" NVDA       # 특정 종목 심층 분석
python scripts/kr_stocks.py                        # 종목명 → 티커 변환 테스트
python scripts/market_indicators.py               # 시장 지표 수집 테스트 (지표 커맨드용)
```

`.env.example`을 `.env`로 복사 후 `ANTHROPIC_API_KEY`, `DISCORD_BOT_TOKEN` 설정 필요.
`FRED_API_KEY` (선택): TIPS 실질금리·HY 스프레드 포함 시 필요. https://fred.stlouisfed.org/docs/api/api_key.html 에서 무료 발급.

**Windows Task Scheduler (자동 실행)**
- `StockResearch_KoreanMarket` — 매일 15:30 국장 마감 리포트
- `StockResearch_DailyReport` — 매일 06:30 미장 마감 전체 리포트
- `StockResearch_DiscordBot` — 로그인 시 봇 자동 시작

재등록 시: `scripts/setup_scheduler.ps1`을 관리자 PowerShell에서 실행.

## Architecture

이 저장소는 세 개의 독립적인 시스템으로 구성됩니다.

---

### 1. 시총 대시보드 (Node.js + React)

Full-stack TypeScript: React+Vite 프론트엔드, Express 백엔드, `data/` 파일 기반 JSON 스토리지.

**Frontend** (`src/`) — 4개 탭 SPA:
- `TodayTab` — 전 세계 시총 Top 200, 섹터 필터링, 데이터 수집 트리거
- `DateTab` — 날짜별 과거 스냅샷 조회
- `RankChangeTab` — 두 날짜 간 순위 변동 비교
- `CountryTab` — 국가별 시총 집계 (Recharts 파이·바 차트)

**Backend** (`server/index.ts`) — Express 라우트 4개:
- `GET /api/dates` — `data/index.json`에서 수집 날짜 목록
- `GET /api/data/:date` — `data/marketcap-YYYY-MM-DD.json` 로드
- `GET /api/meta` — 요약 메타데이터
- `POST /api/collect` — **SSE 스트림**으로 Claude 에이전트 데이터 수집 실행

**데이터 수집 흐름** (핵심 기능):
1. 클라이언트가 `POST /api/collect` → SSE 연결 오픈
2. Claude Sonnet (`claude-sonnet-4-5`) + `web_search_20250305` 도구로 최대 15턴 루프
3. 진행 이벤트: `searching` → `streaming` → `processing` → `done`
4. 파싱된 JSON → `data/marketcap-YYYY-MM-DD.json`, `data/index.json` 업데이트

**데이터 스키마** (`src/types.ts`):
- `StockEntry`: rank, name, ticker, exchange, country, sector, market_cap_usd, market_cap_krw, price_usd, change_1d_pct, collected_at
- `DayData`: date, rate (KRW/USD), data[]
- Sectors: Technology, Finance, Healthcare, Energy, Consumer, Industrial, Other

**UI 규칙**: `src/index.css` CSS 변수 다크 테마 — CSS 프레임워크 추가 금지. UI 텍스트는 한국어. 상승 `#3fb950`, 하락 `#f85149`. 개발 모드에서 `/api/*` 는 Vite가 `localhost:3001`로 프록시.

---

### 2. Discord 리서치 에이전트 팀 (Python)

`scripts/` 아래 Python 스크립트들이 Discord 봇과 자동 리포트를 담당.

**에이전트 흐름**

```
[Task Scheduler 자동 / Discord 슬래시 커맨드]
         ↓
  market_watcher.py      — Top 20 순위변동 감지 → #시장-알림, #일간-요약
  korean_market_report.py — KOSPI 시총 상위 20(실시간) + 워치리스트 → #일간-요약
  sector_analyst.py      — 섹터별 자금흐름 분석 → #섹터-동향
  technical_analyst.py   — RSI·MACD·이평선·52주 고저 (Yahoo Finance) → #종목-분석
  deep_analyst.py        — Claude API + web search 심층 분석 → #종목-분석
         ↑
  discord_bot.py         — 슬래시 커맨드 수신 및 위 스크립트 트리거
  kr_stocks.py           — 한국 종목명 → 티커 변환 유틸 (24h 캐시)
```

**Discord 슬래시 커맨드**

| 커맨드 | 입력 | 설명 |
|--------|------|------|
| `/추가 삼성전자` | 종목명 또는 티커 | 워치리스트 추가 |
| `/삭제 AAPL` | 종목명 또는 티커 | 워치리스트 제거 |
| `/워치리스트` | — | 현재 목록 조회 |
| `/분석 NVDA` | 종목명 또는 티커 | 기술적 분석 (10~20초) |
| `/심층분석 현대차` | 종목명 또는 티커 | Claude 심층 분석 (1~2분) |
| `/지표` | — | 글로벌·한국 시장 지표 현황 |

슬래시 커맨드는 MESSAGE CONTENT INTENT 없이도 작동함 (봇 설정에서 별도 인텐트 불필요).

**한국 종목명 변환 (`kr_stocks.py`)**
- `FinanceDataReader`로 KOSPI/KOSDAQ 전체 목록 수집 후 `data/kr_stocks_cache.json`에 24시간 캐싱
- `resolve_ticker(name)` → `(ticker, name)` 반환. 완전 일치 우선, 부분 일치 시 후보 목록 반환
- 한국 티커 형식: `005930.KS` (KOSPI), `XXXXXX.KQ` (KOSDAQ)

**Discord 채널 → 환경변수 매핑**

| 채널 | 환경변수 |
|------|---------|
| `#시장-알림` | `DISCORD_CH_MARKET_ALERT` |
| `#일간-요약` | `DISCORD_CH_DAILY_SUMMARY` |
| `#종목-분석` | `DISCORD_CH_STOCK_ANALYSIS` |
| `#섹터-동향` | `DISCORD_CH_SECTOR_TREND` |

**워치리스트**: `data/watchlist.json` — `{ticker, name, added_at}` 배열.

**심층 분석 (`deep_analyst.py`)**: `stock-agent.md`와 동일한 7단계 리서치 방식을 Anthropic SDK로 구현. Claude Sonnet + `web_search_20250305` 도구로 주간 성과·주가 사유·경쟁력·밸류에이션·펀더멘털·전망·뉴스·증권사 의견 수집 후 Discord embed 3개(분석·증권사·뉴스)로 전송.

---

### 3. 주식 리서치 에이전트 (Claude Code)

`.claude/agents/stock-agent.md` — `/stock-agent [기업명] [티커]` 명령으로 7단계 WebSearch 파이프라인 실행:
- 결과 JSON: `output/_temp_TICKER.json` → Excel: `output/TICKER_YYYYMMDD.xlsx`
- Excel 생성: `.claude/skills/stock-research-formatter/scripts/make_direct.py`
- 포트폴리오 마스터: `output/portfolio_master.xlsx`
