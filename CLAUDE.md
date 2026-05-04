# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 대화 언어

이 저장소에서 작업할 때는 **한국어**로 응답하세요.

## Commands

**초기 설정**
```bash
npm install                          # Node.js 의존성 설치
pip install -r requirements.txt      # Python 의존성 설치 (discord.py 2.4, anthropic 0.49, yfinance, pandas 2.2, finance-datareader 등)
cp .env.example .env                 # 환경변수 파일 생성 후 편집
```

필수 환경변수 (미설정 시 봇 크래시):
- `ANTHROPIC_API_KEY`, `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`
- `DISCORD_CH_MARKET_ALERT`, `DISCORD_CH_DAILY_SUMMARY`, `DISCORD_CH_STOCK_ANALYSIS`, `DISCORD_CH_SECTOR_TREND`

선택 환경변수:
- `PORT` — Express 서버 포트 (기본값: 3001)
- `FRED_API_KEY` — TIPS 실질금리·HY 스프레드
- `NOTION_API_KEY` + `NOTION_DATABASE_ID` — 뉴스레터 초안 Notion 저장
- `STIBEE_API_KEY` + `STIBEE_LIST_ID_A/B` — Stibee 이메일 캠페인 생성

**Dashboard (Node.js)**
```bash
npm run dev              # 서버(3001) + 클라이언트(5173) 동시 실행
npm run dev:server      # Express 서버만 (tsx watch)
npm run dev:client      # Vite 개발 서버만
npm run build           # 프론트엔드 타입체크(noEmit) + Vite 클라이언트 번들 — 서버는 컴파일 없이 항상 tsx로 실행
npm run preview         # 빌드 결과물 미리보기 (Vite preview)
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
python scripts/portfolio_excel.py output/_temp_portfolio.json  # 포트폴리오 Excel 생성
```

**Newsletter (Python)**
```bash
python scripts/run_newsletter.py A    # 뉴스레터 A 파이프라인 (수집→AI→Notion)
python scripts/run_newsletter.py B    # 뉴스레터 B 파이프라인 (수집→AI→Notion)
```

**Windows Task Scheduler (자동 실행)**
- `StockResearch_DailyReport` — 매일 07:00 글로벌 지표 + 시장 감시 + 섹터 분석
- `StockResearch_KoreanMarket` — 매일 15:31 국장 마감 리포트 + 한국 시장 지표
- `StockResearch_DiscordBot` — 로그인 시 봇 자동 시작
- `StockResearch_Newsletter_A` — 월~금 04:00 뉴스레터 A 파이프라인
- `StockResearch_Newsletter_B` — 화·목·토 04:30 뉴스레터 B 파이프라인

재등록 시: `scripts/setup_scheduler.ps1`을 관리자 PowerShell에서 실행.
봇 재시작 (PowerShell): `schtasks /End /TN "StockResearch_DiscordBot"` → `schtasks /Run /TN "StockResearch_DiscordBot"`

**Docker (Discord 봇 컨테이너)**
```bash
docker build -t stock-bot .  # 최초 또는 requirements.txt 변경 후 빌드
docker-compose up -d         # 백그라운드로 봇 실행
docker-compose logs -f       # 실시간 로그 확인
docker-compose down          # 봇 종료
```
데이터는 `./data:/app/data`, 스크립트는 `./scripts:/app/scripts`로 마운트 — 컨테이너 재시작 없이 스크립트 수정 즉시 반영. 로그는 JSON 드라이버로 10MB × 3개 로테이션.

> **주의**: Docker는 Discord 봇(`discord_bot.py`)만 실행. `docker/entrypoint.sh`와 `docker/crontab`은 준비됐지만 현재 Dockerfile의 CMD에 연결되지 않음 — 스케줄 작업(07:00, 15:31, 뉴스레터)은 Windows Task Scheduler가 담당.

## Architecture

이 저장소는 네 개의 독립적인 시스템으로 구성됩니다.

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
2. `claude-sonnet-4-5` + `web_search_20250305` 도구로 최대 15턴 루프 (`server/index.ts:107` 하드코딩 — 에이전트 버전 4.6과 다름)
3. 진행 이벤트: `searching` → `streaming` → `processing` → `done`
4. 파싱된 JSON → `data/marketcap-YYYY-MM-DD.json`, `data/index.json` 업데이트

**데이터 스키마** (`src/types.ts`):
- `StockEntry`: rank, name, ticker, exchange, country, sector, market_cap_usd, market_cap_krw, price_usd, change_1d_pct, collected_at
- `DayData`: date, rate (KRW/USD), data[]
- Sectors: Technology, Finance, Healthcare, Energy, Consumer, Industrial, Other

**UI 규칙**: `src/index.css` CSS 변수 다크 테마 — CSS 프레임워크 추가 금지. UI 텍스트는 한국어. 상승 `#3fb950`, 하락 `#f85149`. 개발 모드에서 `/api/*` 는 Vite가 `localhost:3001`로 프록시.

**TypeScript 설정 구분**:
- `tsconfig.json` — `src/`(프론트엔드) 전용, `"noEmit": true` → 타입체크만, 파일 출력 없음
- `tsconfig.server.json` — `server/` 전용, `outDir: "dist-server"` → `npm run build`에 포함되지 않음. 서버는 개발·프로덕션 모두 `tsx`로 직접 실행

---

### 2. Discord 리서치 에이전트 팀 (Python)

`scripts/` 아래 Python 스크립트들이 Discord 봇과 자동 리포트를 담당.

**자동 발송 스케줄**

| 시각 | 실행 주체 | 내용 | 채널 |
|------|-----------|------|------|
| 07:00 | Task Scheduler → `run_daily.py` | 글로벌 지수·변동성 + 금리·통화·원자재 | #일간-요약 |
| 07:00 | Task Scheduler → `run_daily.py` | 시총 Top 20 일간 요약 | #일간-요약 |
| 07:00 | Task Scheduler → `run_daily.py` | Top 10 순위변동 감지 (변동 시만) | #시장-알림 |
| 07:00 | Task Scheduler → `run_daily.py` | 워치리스트 급변 ±5% (있을 때만) | #시장-알림 |
| 07:00 | Task Scheduler → `run_daily.py` | 섹터별 자금흐름 | #섹터-동향 |
| 장중 3분 주기 | Discord 봇 내부 | 워치리스트 전체 + KOSPI 상위 20 급변 ±5% (평일, 한국장 09:00~15:30 / 미국장 22:00~06:00) | #시장-알림 |
| 15:31 | Task Scheduler → `korean_market_report.py` | 국장 마감 리포트 (KOSPI 상위 20 + 워치리스트 한국 종목) + 한국 시장 지표 | #일간-요약 |

**에이전트 흐름**

```
[Task Scheduler 자동 / Discord 슬래시 커맨드]
         ↓
  market_watcher.py       — Top 20 순위변동 감지 → #시장-알림, #일간-요약
  market_indicators.py    — 글로벌·한국 시장 지표 수집 및 전송 (run_global / run_korea)
  korean_market_report.py — KOSPI 시총 상위 20(실시간) + 워치리스트 → #일간-요약 (15:31)
  sector_analyst.py       — 섹터별 자금흐름 분석 → #섹터-동향
  technical_analyst.py    — RSI·MACD·이평선·52주 고저 (Yahoo Finance) → #종목-분석
  deep_analyst.py         — Claude API + web search 심층 분석 → #종목-분석
         ↑
  discord_bot.py          — 슬래시 커맨드 수신 + 장중 3분 주기 실시간 급변 감지
  kr_stocks.py            — 한국 종목명 → 티커 변환 유틸 (24h 캐시)
  yahoo_finance.py        — Yahoo Finance 래퍼 (fast_info 우선, 5d 일별 폴백)
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

**실시간 급변 감지 (`discord_bot.py` — `realtime_watchlist_alert`)**:
- 폴링 주기: **3분** (`@tasks.loop(minutes=3)`) — 장중에만 실행
- 대상: 워치리스트 전체(한국+미국) + KOSPI 시총 상위 20 (한국장 시간에만 추가)
- 기준: 전일 종가 대비 ±5% (`ALERT_THRESHOLD_PCT = 5.0`)
- 중복 방지: `_alerted` dict로 당일 알림 완료 티커 추적, 자정 초기화
- `yahoo_finance.get_intraday_change()` — `fast_info` 우선, 실패 시 5d 일별 데이터로 폴백

**심층 분석 (`deep_analyst.py`)**: `stock-agent.md`와 동일한 7단계 리서치 방식을 Anthropic SDK로 구현. Claude Sonnet + `web_search_20250305` 도구로 주간 성과·주가 사유·경쟁력·밸류에이션·펀더멘털·전망·뉴스·증권사 의견 수집 후 Discord embed 3개(분석·증권사·뉴스)로 전송.

---

### 3. Claude Code 에이전트 슬래시 커맨드

`.claude/agents/` 폴더의 에이전트들은 Claude Code에서 슬래시 커맨드로 직접 실행합니다.

| 커맨드 | 모델 | 설명 |
|--------|------|------|
| `/stock-agent [기업명] [티커]` | Sonnet 4.6 | 7단계 WebSearch → Excel 개별+포트폴리오 리포트 |
| `/deep-analyst [기업명] [티커]` | Haiku 4.5 | `deep_analyst.py` 실행 → Discord #종목-분석 (1~2분) |
| `/technical-analyst [티커...]` | Haiku 4.5 | `technical_analyst.py` 실행 → Discord #종목-분석 |
| `/market-watcher` | Haiku 4.5 | `market_watcher.py` 실행 → Discord #시장-알림·#일간-요약 |
| `/korean-market` | Haiku 4.5 | `korean_market_report.py` 실행 → Discord #일간-요약 |
| `/sector-analyst` | Haiku 4.5 | `sector_analyst.py` 실행 → Discord #섹터-동향 |
| `/portfolio-analyzer [이미지1] [이미지2]` | Sonnet 4.6 | 스크린샷에서 목표비중·보유현황 추출 → Excel 리포트 생성 |
| `/newsletter [A\|B]` | Haiku 4.5 | 뉴스레터 파이프라인 실행 (RSS 수집 → AI 초안 → Notion) |

> **주의 — 에이전트 파일 내 절대 경로**: `.claude/agents/stock-agent.md`의 파일 경로가 구 OneDrive 경로(`C:\Users\kukuk\OneDrive\바탕 화면\business\STOCK\`)로 하드코딩돼 있음. 현재 작업 디렉터리는 `D:\business\STOCK`. 에이전트가 파일을 잘못된 위치에 쓰는 경우 해당 파일의 경로를 일괄 수정할 것.

**stock-agent 출력물**:
- 리서치 마크다운: `research/TICKER_YYYYMMDD.md` — `/stock-research-formatter`가 이 파일을 읽어 Excel 생성
- JSON 임시파일: `output/_temp_TICKER.json` (완료 후 자동 삭제)
- 개별 리포트: `output/TICKER_YYYYMMDD.xlsx`
- 포트폴리오 마스터: `output/portfolio_master.xlsx`
- Excel 생성 스크립트: `.claude/skills/stock-research-formatter/scripts/make_direct.py`

**portfolio-analyzer 동작**:
- 인자 2개: 첫 번째=목표비중 이미지, 두 번째=보유현황 이미지 → `data/target_portfolio.json` 갱신 후 Excel
- 인자 1개: `data/target_portfolio.json` 기존값 사용, 인자=보유현황 이미지 → Excel
- `data/target_portfolio.json` — 목표 포트폴리오 설정 (`total_investment`, `stocks[]` 배열). 종목명 매칭은 부분 일치 허용.
- 출력: `output/portfolio_status_YYYYMMDD_HHmm.xlsx`

---

### 4. 뉴스레터 자동화 (Python)

`scripts/run_newsletter.py`가 4단계 파이프라인을 순서대로 실행합니다. Stibee 발송은 자동화하지 않고 캠페인 생성까지만 수행 — 이후 수동 발송.

**파이프라인 흐름**

```
run_newsletter.py [A|B]
  1. newsletter_collect.py  — RSS 피드 + 시장 데이터 수집 → data/_temp_newsletter_{ID}.json
  2. newsletter_ai.py       — Haiku(사실 추출) + Sonnet(본문 생성) → research/newsletter_{ID}_{YYYYMMDD}.md
  3. newsletter_notion.py   — Notion DB에 초안 페이지 업로드 (NOTION_API_KEY 없으면 건너뜀)
```
Stibee 발송은 파이프라인에서 제외 — Notion 검수 후 Stibee 대시보드에서 수동 발송.

**뉴스레터 구분**
- A: 글로벌 정치경제 — 월~금 04:00 자동 실행, 06:30 수동 발송
- B: AI 트렌드 — 화·목·토 04:30 자동 실행, 07:00 수동 발송

**설정 파일**: `data/newsletter_config_{A|B}.json` — 구독자 목록·RSS 소스·템플릿 등 뉴스레터별 설정.
