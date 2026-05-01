# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Dashboard (Node.js)**
```bash
npm run dev              # Run both server (port 3001) and client (port 5173) concurrently
npm run dev:server      # Express server only, with tsx watch
npm run dev:client      # Vite dev server only
npm run build           # tsc compile server, then vite build client → dist/ and dist-server/
```

**Discord Agent Team (Python)**
```bash
python scripts/discord_bot.py           # Discord 봇 실행 (수동)
python scripts/run_daily.py             # 미장 마감 후 전체 리포트 일괄 실행
python scripts/korean_market_report.py  # 국장 마감 리포트 단독 실행
python scripts/technical_analyst.py AAPL TSLA  # 특정 종목 기술적 분석
```

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` and `DISCORD_BOT_TOKEN` before running.

**Windows Task Scheduler (자동 실행)**
- `StockResearch_KoreanMarket` — 매일 15:30 국장 마감 리포트
- `StockResearch_DailyReport` — 매일 06:30 미장 마감 전체 리포트
- `StockResearch_DiscordBot` — 로그인 시 봇 자동 시작

## Architecture

이 저장소는 두 개의 독립적인 시스템으로 구성됩니다.

---

### 1. 시총 대시보드 (Node.js + React)

Full-stack TypeScript: React+Vite 프론트엔드, Express 백엔드, `data/` 아래 파일 기반 JSON 스토리지.

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
1. 클라이언트가 `POST /api/collect` 호출 → SSE 연결 오픈
2. Claude Sonnet (`claude-sonnet-4-5`) + web search tool (`web_search_20250305`) 실행
3. Claude가 최대 15턴 루프로 웹 검색 → JSON 반환
4. 진행 이벤트 스트리밍: `searching` → `streaming` → `processing` → `done`
5. 파싱된 JSON을 `data/marketcap-YYYY-MM-DD.json`에 저장, `data/index.json` 업데이트

**데이터 스키마** (`src/types.ts`):
- `StockEntry`: rank, name, ticker, exchange, country, sector, market_cap_usd, market_cap_krw, price_usd, change_1d_pct, collected_at
- `DayData`: date, rate (KRW/USD), data[]
- Sectors: Technology, Finance, Healthcare, Energy, Consumer, Industrial, Other

**Key Files**

| 파일 | 역할 |
|------|------|
| `server/index.ts` | 모든 백엔드 라우트 + Claude API 연동 |
| `src/App.tsx` | 탭 라우터, 메타데이터 로딩, 헤더 |
| `src/components/CollectButton.tsx` | SSE 클라이언트, 스트리밍 UI |
| `src/types.ts` | 공유 TypeScript 인터페이스 |
| `src/utils.ts` | fmtUSD, fmtKRW, fmtChange, 국기 이모지 헬퍼 |
| `vite.config.ts` | 개발 프록시 `/api/*` → `localhost:3001` |

개발 모드에서 `/api` 요청은 `localhost:3001`로 프록시됨. 프로덕션에서는 Express가 `dist/` 정적 파일도 직접 서빙해야 함.

**UI 규칙**: `src/index.css` CSS 변수로 다크 테마 적용 — CSS 프레임워크 도입 금지. UI 텍스트는 한국어. 상승 `#3fb950`, 하락 `#f85149`.

---

### 2. Discord 리서치 에이전트 팀 (Python)

`scripts/` 아래 Python 스크립트들이 Discord 봇과 자동 리포트를 담당.

**에이전트 구조**

```
[트리거: Task Scheduler / Discord 명령]
         ↓
  market_watcher.py     — Top 20 순위변동 감지 → #시장-알림, #일간-요약
  korean_market_report.py — KOSPI 시총 상위 20 실시간 + 워치리스트 → #일간-요약
  sector_analyst.py     — 섹터별 자금흐름 분석 → #섹터-동향
  technical_analyst.py  — RSI·MACD·이평선·52주 고저 → #종목-분석
         ↑
  discord_bot.py        — 자연어 명령 수신, 위 스크립트 트리거
```

**Discord 채널 → 환경변수 매핑**

| 채널 | 환경변수 |
|------|---------|
| `#시장-알림` | `DISCORD_CH_MARKET_ALERT` |
| `#일간-요약` | `DISCORD_CH_DAILY_SUMMARY` |
| `#종목-분석` | `DISCORD_CH_STOCK_ANALYSIS` |
| `#섹터-동향` | `DISCORD_CH_SECTOR_TREND` |

**Discord 봇 자연어 명령 예시**
- `추가 AAPL` / `005930.KS 추가해줘` — 워치리스트 추가
- `삭제 AAPL` / `빼줘 009150.KS` — 워치리스트 제거
- `목록` / `워치리스트` — 현재 목록 조회
- `분석 NVDA` — 기술적 분석 즉시 실행

한국 주식 티커 형식: `005930.KS` (KOSPI), `005930.KQ` (KOSDAQ). 워치리스트는 `data/watchlist.json`에 저장.

**KOSPI 시총 상위** — `korean_market_report.py`가 `FinanceDataReader`로 실시간 상위 20개 조회. Yahoo Finance(`yfinance`)로 가격·기술지표 수집.

---

### 3. 주식 리서치 에이전트 (Claude)

`.claude/agents/stock-agent.md` — `/stock-agent [기업명] [티커]` 명령으로 7단계 WebSearch 파이프라인 실행:
- 결과: `research/TICKER_YYYYMMDD.md`
- Excel 리포트: `.claude/skills/stock-research-formatter/` Python 스크립트
- 포트폴리오: `output/portfolio_master.xlsx`
