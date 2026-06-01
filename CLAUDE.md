# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 언어 설정

이 저장소의 모든 커뮤니케이션은 **한국어**를 기본으로 합니다.

- **응답·설명**: 모든 사용자 응답, 진행 상황 업데이트, 요약은 한국어로 작성
- **커밋 메시지**: 한국어로 작성 (예: `시총 수집 실패 시 알림 추가`). Co-Authored-By 트레일러 등 표준 영문 메타데이터는 그대로 유지
- **PR 제목·본문**: 한국어로 작성
- **계획·태스크 목록**: TaskCreate, ExitPlanMode 등에서 사용하는 작업 항목도 한국어
- **코드 주석**: 새로 추가하는 주석은 한국어 (단, 기본 규칙에 따라 주석 자체를 최소화 — WHY가 비자명할 때만 작성)
- **문서**: README, 기술 문서, CLAUDE.md 등 마크다운 문서는 한국어
- **로그 메시지**: 사용자/운영자가 읽는 로그는 한국어 권장
- **예외**: 변수명·함수명·파일명·식별자·라이브러리 API·에러 메시지 원문·외부 시스템 키워드는 영문 유지

## 작업 방식

이 저장소에서는 **확인 질문을 최소화하고 합리적 판단으로 즉시 작업**합니다.

- **선택 질문(AskUserQuestion) 금지 (기본)**: 이미지 선택, 옵션 분기, 진행 여부 확인 등을 사용자에게 묻지 말고 합리적인 디폴트로 진행 후 결과를 보고. 예: portfolio-analyzer에 인자만 들어오면 그대로 실행, 캡처 자동 저장 같은 유틸리티는 바로 설정·실행
- **합리적 디폴트 선택 기준**: ① 사용자가 직전에 언급한 의도, ② 폴더 컨벤션·기존 설정 파일, ③ 가장 최근 데이터 사용
- **실행 후 보고**: 무엇을 가정하고 무엇을 실행했는지 결과와 함께 1~2줄로 명시. 가정이 틀렸으면 사용자가 되돌릴 수 있음
- **여전히 확인이 필요한 작업** (CLAUDE.md 자율화 범위 밖):
  - `git push`, `git push --force`, `git reset --hard` 등 원격/되돌릴 수 없는 git 작업
  - 외부 시스템 발송: Discord 메시지, 뉴스레터 Stibee/Gmail 발송, Notion 업로드
  - `output/`·`data/` 외부의 사용자 개인 파일 다량 삭제·이동
  - 환경변수·API 키 노출 가능성이 있는 작업
- **태스크 추적**: 다단계 작업은 묻지 말고 TaskCreate로 시작, 진행 상황을 사용자가 볼 수 있게 함

## Commands

**초기 설정**
```bash
npm install                          # Node.js 의존성 설치
pip install -r requirements.txt      # Python 의존성 설치 (discord.py 2.4, anthropic 0.49, yfinance, pandas 2.2, finance-datareader 등)
pip install openpyxl                 # Excel 생성용 (requirements.txt 미포함 — 누락 시 stock-agent/portfolio-analyzer 실패)
cp .env.example .env                 # 환경변수 파일 생성 후 편집
```

> PC 포맷 후 환경 복구 절차는 `README.md` 참조 (`.env`·`target_portfolio.json`·`watchlist.json` 백업 항목, Node/Python 설치 순서 포함).

필수 환경변수 (미설정 시 봇 크래시):
- `ANTHROPIC_API_KEY`, `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`
- `DISCORD_CH_MARKET_ALERT`, `DISCORD_CH_DAILY_SUMMARY`, `DISCORD_CH_STOCK_ANALYSIS`, `DISCORD_CH_SECTOR_TREND`

선택 환경변수:
- `PORT` — Express 서버 포트 (기본값: 3001)
- `FRED_API_KEY` — TIPS 실질금리·HY 스프레드
- `NOTION_API_KEY` + `NOTION_DATABASE_ID_A` + `NOTION_DATABASE_ID_B` — 뉴스레터 A/B 별도 Notion DB 저장
- `STIBEE_API_KEY` + `STIBEE_LIST_ID_A/B` — Stibee 구독자 목록 조회 (`newsletter_send.py`) + 캠페인 생성 (`newsletter_stibee.py`)

**Dashboard (Node.js)**
```bash
npm run dev              # 서버(3001) + 클라이언트(5173) 동시 실행
npm run dev:server      # Express 서버만 (tsx watch)
npm run dev:client      # Vite 개발 서버만
npm run build           # 프론트엔드 타입체크(noEmit) + Vite 클라이언트 번들 — 서버는 컴파일 없이 항상 tsx로 실행
npm run preview         # 빌드 결과물 미리보기 (Vite preview)
```

> **테스트·린터 없음**: 이 저장소에는 단위 테스트, 통합 테스트, ESLint 설정이 없음. 타입 검사만 `npm run build`(프론트엔드) 또는 `tsc -p tsconfig.json --noEmit`으로 가능.

**Discord Agent Team (Python)**
```bash
python scripts/discord_bot.py                      # Discord 봇 실행 (수동)
python scripts/run_daily.py                        # 미장 마감 후 전체 리포트 일괄 실행 (시총 수집 포함)
python scripts/collect_marketcap_live.py           # yfinance로 글로벌 시총 실시간 수집 → data/ 저장
python scripts/korean_market_report.py             # 국장 마감 리포트 단독 실행
python scripts/technical_analyst.py AAPL TSLA      # 특정 종목 기술적 분석
python scripts/deep_analyst.py "NVIDIA" NVDA       # 특정 종목 심층 분석
python scripts/kr_stocks.py                        # 종목명 → 티커 변환 테스트
python scripts/market_indicators.py               # 시장 지표 수집 테스트 (지표 커맨드용)
python scripts/portfolio_excel.py <holdings_json_path>  # 포트폴리오 Excel 생성
# holdings_json 형식: {"total_value": 137906438, "holdings": [{"name": "삼성전자", "value": 29350900}, ...]}
```

**Newsletter (Python)**
```bash
python scripts/run_newsletter.py A    # 뉴스레터 A 파이프라인 (수집→AI→검수→Notion)
python scripts/run_newsletter.py B    # 뉴스레터 B 파이프라인 (수집→AI→검수→Notion)
python scripts/newsletter_send.py A   # Stibee 구독자 목록 조회 + Gmail SMTP 발송
python scripts/newsletter_send.py B   # 뉴스레터 B 발송
python scripts/newsletter_stibee.py A # Stibee 캠페인 생성 (발송은 Stibee 대시보드에서 수동)
```

선택 환경변수 (`newsletter_send.py` 발송에 필요):
- `GMAIL_USER` + `GMAIL_APP_PASSWORD` — Gmail SMTP 발신자 계정 (앱 비밀번호 16자리, 없으면 발송 단계 즉시 실패)

**Windows Task Scheduler (자동 실행)**
- `StockResearch_DiscordBot` — ~~로그인 시 봇 자동 시작~~ **비활성화됨** (NAS를 주봇으로 사용, 이중 실행 시 10062 오류)
- `StockResearch_DailyReport` — ~~07:00 일간 리포트~~ **비활성화됨** (NAS Docker cron이 담당. 활성화 시 NAS와 중복 전송 발생. `StartWhenAvailable=true`라 PC 켜지는 순간 즉시 실행되므로 반드시 비활성화)
- `StockResearch_KoreanMarket` — ~~16:00 국장 마감 리포트~~ **비활성화됨** (NAS Docker cron이 담당. 동일 이유)
- `StockResearch_Newsletter_A` — 매일 04:50 뉴스레터 A 파이프라인 (NAS로 이전 권장)
- `StockResearch_Newsletter_B` — 매일 05:00 뉴스레터 B 파이프라인 (NAS로 이전 권장)

> **주의**: 07:00 일간 리포트와 16:00 국장 리포트는 NAS Docker cron이 담당. Windows Task Scheduler와 중복 등록 시 Discord 메시지가 두 번 전송됨.
> **이중 봇 문제**: PC 봇과 NAS 봇이 동시에 실행되면 Discord가 같은 슬래시 커맨드 인터랙션을 양쪽에 전달해 한쪽이 `10062 Unknown interaction` 오류로 실패함. NAS가 주봇 — PC Task Scheduler의 `StockResearch_DiscordBot`은 비활성화 상태 유지. `discord_bot.py`의 `_defer()` 헬퍼가 10062를 조용히 무시하도록 처리돼 있음.

재등록 시: `scripts/setup_scheduler.ps1`을 관리자 PowerShell에서 실행 (`StockResearch_Newsletter_A/B` 등록, `StockResearch_DiscordBot`은 NAS 주봇 원칙으로 등록하지 않음).
PC 봇 중지: `schtasks /End /TN "StockResearch_DiscordBot"`

**NAS 컨테이너 경로**: `/volume1/docker/stock` (주의: `/volume1/docker/stock-bot`은 구버전 디렉토리)
- WinSCP 스크립트 업로드: `D:\business\STOCK\scripts\` → `/volume1/docker/stock/scripts/`
- 업로드 후 재시작 불필요 (볼륨 마운트로 즉시 반영). 단 `docker/` 하위 파일 변경 시 `sudo docker restart stock-bot` 필요.

**Docker (Discord 봇 컨테이너)**
```bash
docker build -t stock-bot .  # 최초 또는 requirements.txt 변경 후 빌드
docker-compose up -d         # 백그라운드로 봇 실행 (로컬 PC용)
docker-compose logs -f       # 실시간 로그 확인
docker-compose down          # 봇 종료
```
볼륨 마운트: `./data:/app/data`, `./scripts:/app/scripts`, `./research:/app/research`, `./logs:/app/logs`, `./.env:/app/.env:ro` — 컨테이너 재시작 없이 스크립트 수정 즉시 반영. 로그는 JSON 드라이버로 10MB × 3개 로테이션.

`docker-compose.nas.yml` — NAS 전용 설정 (`docker-compose.yml`에서 볼륨 경로를 `/volume1/docker/stock/`으로 교체). NAS에서는 이 파일을 사용.

> **NAS 최초 배포 시**: `logs/` 디렉토리가 없으면 컨테이너 시작 실패. `mkdir -p /volume1/docker/stock/logs` 먼저 실행할 것.

> **cron 동작 확인**: `python:3.12-slim` 이미지에는 `ps` 명령어가 없음. cron 실행 여부는 `docker exec stock-bot /usr/sbin/cron` 실행 시 `can't lock /var/run/crond.pid` 메시지로 확인 (이미 실행 중이라는 의미).

> **Container Manager 로그탭이 비어있을 경우**: WinSCP로 `/volume1/docker/stock/logs/` 폴더를 직접 열어 확인. `docker-compose.nas.yml`에서 `logging` 블록 제거로 해결 가능 (현재 제거됨).
>
> **NAS 로그 파일 목록** (`/volume1/docker/stock/logs/`):
> - `daily.log` — 07:00 시총 수집 + 글로벌 지표 + 시장 요약
> - `korean.log` — 16:00 국장 마감 리포트
> - `newsletter_A.log` — 04:50 뉴스레터 A 파이프라인
> - `newsletter_B.log` — 05:00 뉴스레터 B 파이프라인
> - `newsletter_send_A.log` — 05:59 뉴스레터 A 발송
> - `newsletter_send_B.log` — 06:00 뉴스레터 B 발송

> **NAS scripts 동기화**: `scripts/` 파일은 볼륨 마운트로 즉시 반영되지만 NAS에 파일이 없으면 반영되지 않음. 새 스크립트 추가 후 WinSCP로 `/volume1/docker/stock/scripts/`에 업로드 필수. 누락 시 `ModuleNotFoundError` 발생. 특히 `collect_marketcap_live.py`가 없으면 07:00 일간 리포트 전체 실패.

> **NAS 배포 기준**: `docker/entrypoint.sh`가 Dockerfile CMD로 연결돼 있어 컨테이너 시작 시 cron 데몬 + Discord 봇이 함께 실행됨. cron 스케줄 작업(04:50·05:00·05:59·06:00 뉴스레터, 07:00 일간 리포트, 16:00 국장 리포트)은 컨테이너 내부 cron이 담당. cron 스크립트는 `load_dotenv()`로 `/app/.env`를 읽으므로 반드시 `.env` 볼륨 마운트가 있어야 함. PC가 꺼져 있어도 NAS에서 모든 자동화가 실행되는 것이 목표. Windows Task Scheduler와 중복 등록 금지 — Discord 메시지 이중 발송 원인.

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
2. `claude-sonnet-4-5` + `web_search_20250305` 도구로 최대 15턴 루프 (`server/index.ts`에서 `model:` 키워드로 검색해 모델명 수정 — 라인 번호는 코드 변경으로 이동할 수 있음)
3. 진행 이벤트: `searching` → `streaming` → `processing` → `done`
4. 파싱된 JSON → `data/marketcap-YYYY-MM-DD.json`, `data/index.json` 업데이트

**데이터 스키마** (`src/types.ts`):
- `StockEntry`: rank, name, ticker, exchange, country, sector, market_cap_usd, market_cap_krw, price_usd, change_1d_pct, collected_at
- `DayData`: date, rate (KRW/USD), data[]
- `Sector` (UI 필터 타입): `All | Technology | Finance | Healthcare | Energy | Consumer | Industrial | Other` — UI 드롭다운용 축약 목록. JSON 데이터의 sector 필드는 Claude 에이전트가 할당하는 더 넓은 값(Communication Services, Conglomerate, Materials 등)을 가질 수 있으며 "Other"로 합산됨.

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
| 07:00 | NAS Docker cron → `run_daily.py` | 시총 수집(yfinance) + 글로벌 지수·변동성 + 금리·통화·원자재 | #일간-요약 |
| 07:00 | NAS Docker cron → `run_daily.py` | 시총 Top 20 일간 요약 | #일간-요약 |
| 07:00 | NAS Docker cron → `run_daily.py` | Top 10 순위변동 감지 (변동 시만) | #일간-요약 |
| 07:00 | NAS Docker cron → `run_daily.py` | 섹터별 자금흐름 | #섹터-동향 |
| 장중 3분 주기 | Discord 봇 내부 | 워치리스트 전체 + KOSPI 상위 20 급변 ±5% (평일, 한국장 09:00~15:30 / 미국장 22:00~06:00) | #시장-알림 |
| 16:00 | NAS Docker cron → `korean_market_report.py` | 국장 마감 리포트 (KOSPI 상위 20 + 워치리스트 한국 종목) + 한국 시장 지표 | #일간-요약 |

**에이전트 흐름**

```
[NAS Docker cron 자동 / Discord 슬래시 커맨드]
         ↓
  collect_marketcap_live.py — yfinance로 글로벌 시총 ~120개 실시간 수집 → data/marketcap-YYYY-MM-DD.json
  market_watcher.py         — Top 20 순위변동 감지 → #일간-요약
  market_indicators.py      — 글로벌·한국 시장 지표 수집 및 전송 (run_global / run_korea)
  korean_market_report.py   — KOSPI 시총 상위 20(실시간) + 워치리스트 → #일간-요약 (16:00)
  sector_analyst.py         — 섹터별 자금흐름 분석 → #섹터-동향
  technical_analyst.py      — RSI·MACD·이평선·52주 고저 (Yahoo Finance) → #종목-분석
  deep_analyst.py           — Claude API + web search 심층 분석 → #종목-분석
         ↑
  discord_bot.py            — 슬래시 커맨드 수신 + 장중 3분 주기 실시간 급변 감지 (APScheduler 없음 — 07:00 스케줄은 NAS cron 전담)
  kr_stocks.py              — 한국 종목명 → 티커 변환 유틸 (24h 캐시)
  yahoo_finance.py          — Yahoo Finance 래퍼 (fast_info 우선, 5d 일별 폴백)
```

> **중복 실행 주의**: `discord_bot.py`에 APScheduler로 07:00 일간 리포트를 등록하면 NAS cron과 이중 실행되어 Discord에 동일 메시지가 두 번 전송됨. 봇은 실시간 알림·슬래시 커맨드만 담당, 정기 리포트는 cron 전담으로 유지할 것.

> **collect 실패 시 동작**: `run_daily.py`는 `collect_and_save()`가 None 반환(yfinance 수집 실패)하면 `market_watcher`·`sector_analyst` 실행을 건너뜀. 오래된 데이터로 잘못된 리포트가 발송되는 것을 방지. `market_indicators`는 시총 데이터와 무관하므로 항상 실행됨.

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
- 중복 방지: `_alerted` dict로 당일 알림 완료 티커 추적, 자정 초기화 (`data/_alerted.json`에 영속화 — 봇 재시작 시 복원)
- `yahoo_finance.get_intraday_change()` — `fast_info` 우선, 실패 시 5d 일별 데이터로 폴백
- **미국장 시간**: 평일 KST 22:00~ 또는 토요일 KST 00:00~06:00 (금요일 미장이 KST 토요일 05:00까지 — 단순 `weekday<5` 체크 시 토요일 새벽 구간 누락됨)
- **Discord 재연결 안전**: `on_ready()` 재호출 시 `is_running()` 체크로 중복 `start()` 방지

**심층 분석 (`deep_analyst.py`)**: `stock-agent.md`와 동일한 7단계 리서치 방식을 Anthropic SDK로 구현. Claude Sonnet + `web_search_20250305` 도구로 주간 성과·주가 사유·경쟁력·밸류에이션·펀더멘털·전망·뉴스·증권사 의견 수집 후 Discord embed 3개(분석·증권사·뉴스)로 전송.

---

### 3. Claude Code 에이전트 슬래시 커맨드

**구조 구분**:
- `.claude/agents/` — AI 서브에이전트 정의 (markdown 프롬프트). Claude Code가 슬래시 커맨드로 로드해 별도 AI 컨텍스트로 실행.
- `.claude/skills/` — Claude Code 스킬 (Python 스크립트 + 지시 파일). `scripts/` 하위에 실행 스크립트가 있음.

`.claude/agents/` 폴더의 에이전트들은 Claude Code에서 슬래시 커맨드로 직접 실행합니다.

| 커맨드 | 모델 | 설명 |
|--------|------|------|
| `/stock-agent [기업명] [티커]` | Sonnet 4.6 | 7단계 WebSearch → Excel 개별+포트폴리오 리포트 |
| `/deep-analyst [기업명] [티커]` | Haiku 4.5 | `deep_analyst.py` 실행 → Discord #종목-분석 (1~2분) |
| `/technical-analyst [티커...]` | Haiku 4.5 | `technical_analyst.py` 실행 → Discord #종목-분석 |
| `/market-watcher` | Haiku 4.5 | `market_watcher.py` 실행 → Discord #일간-요약 |
| `/korean-market` | Haiku 4.5 | `korean_market_report.py` 실행 → Discord #일간-요약 |
| `/sector-analyst` | Haiku 4.5 | `sector_analyst.py` 실행 → Discord #섹터-동향 |
| `/portfolio-analyzer [이미지1] [이미지2]` | Sonnet 4.6 | 스크린샷에서 목표비중·보유현황 추출 → Excel 리포트 생성 |
| `/newsletter [A\|B]` | Haiku 4.5 | 뉴스레터 파이프라인 실행 (RSS 수집 → AI 초안 → Notion) |

**stock-agent 출력물**:
- 리서치 마크다운: `research/TICKER_YYYYMMDD.md` — `/stock-research-formatter`가 이 파일을 읽어 Excel 생성
- JSON 임시파일: `output/_temp_TICKER.json` (파이프라인 중간 결과물 — 자동 삭제되지 않음, 수동 정리 필요)
- 개별 리포트: `output/TICKER_YYYYMMDD.xlsx`
- 포트폴리오 마스터: `output/portfolio_master.xlsx` (실행마다 누적 업데이트)

**stock-research-formatter 스크립트 구분** (`.claude/skills/stock-research-formatter/scripts/`):
- `make_direct.py` — JSON `_temp_*.json` → 개별 Excel + 포트폴리오 마스터 동시 생성 (stock-agent 내부에서 호출)
- `make_individual.py` — 마크다운 `research/*.md` → 개별 Excel 한 파일 생성 (`/stock-research-formatter` 스킬에서 호출)
- `make_portfolio.py` — 마크다운 `research/*.md` → 누적 `portfolio_master.xlsx` 추가/갱신 (`--bulk` 플래그로 폴더 일괄 처리 가능)

**portfolio-analyzer 동작**:
- **이미지 기본 경로**: `C:\Users\kukuk\Pictures\Screenshots` — 날짜(`2026-05-08`, `오늘`) 또는 `최신 N개` 표현으로 이미지 선택. PowerShell로 디렉토리 조회 후 목록 확인 → 역할(목표비중/보유현황) 지정. 절대경로 직접 입력도 가능.
- 인자 2개: 첫 번째=목표비중 이미지, 두 번째=보유현황 이미지 → `data/target_portfolio.json` 갱신 후 Excel
- 인자 1개: `data/target_portfolio.json` 기존값 사용, 인자=보유현황 이미지 → Excel
- **보유현황 이미지 여러 장**: 목표비중 1장 + 보유현황 N장 전달 가능. 여러 계좌(국내계좌1, 국내계좌2, 미국계좌 등) 스크린샷을 모두 전달하면 합산 처리. 동일 종목이 여러 계좌에 있으면 매입금액 합산.
- 보유현황에서 추출하는 값은 **매입금액** 기준. 계산 우선순위: ① 매입금액 직접 표시 ② 매입가 × 보유수량 ③ 평가금액 - 평가손익 ④ 불가 시 제외 후 안내.
- **미국 주식 환율**: 매 실행 시 WebSearch로 현재 USD/KRW 환율 검색 후 적용. 검색 실패 시에만 1,400원 가정.
- **총 투자금액**: 전체 보유 종목 매입금액 합산으로 자동 계산 (이미지 표시값 무시).
- 보유수량·평가금액·매입가 등 계산에 필요한 정보가 모두 없는 종목은 분석 제외 후 사용자에게 안내.
- `data/target_portfolio.json` — 목표 포트폴리오 설정 (`total_investment`, `stocks[]` 배열). 종목명 매칭은 부분 일치 허용. 브로커 화면 별칭 → 정식명 자동 매핑: `scripts/portfolio_excel.py`의 `STOCK_NAME_MAPPING` 딕셔너리에 정의 (예: `LIG디펜스앤에어로` / `LIG넥스원` / `LIG D&A` → `LIG디펜스앤에어로스페이스`). 새로운 매핑이 필요하면 해당 딕셔너리에 추가.
- **삼성전자 + 삼성전자우 합산**: 보유현황에 두 종목이 모두 있으면 매입금액을 합산해 `삼성전자(우선주 포함)`으로 단일 표시. target_portfolio.json의 `삼성전자` 항목에 매칭해 비중 비교.
- 출력: `output/portfolio_status_YYYYMMDD_HHmm.xlsx`

---

### 4. 뉴스레터 자동화 (Python)

`scripts/run_newsletter.py`가 4단계 파이프라인을 순서대로 실행합니다. Stibee 발송은 자동화하지 않고 캠페인 생성까지만 수행 — 이후 수동 발송.

**파이프라인 흐름**

```
run_newsletter.py [A|B]
  1. newsletter_collect.py  — RSS 피드 + 시장 데이터 수집 → data/_temp_newsletter_{ID}.json
  2. newsletter_ai.py       — Haiku(사실 추출) + Sonnet(본문 생성) → research/newsletter_{ID}_{YYYYMMDD}.md
  3. newsletter_review.py   — Claude Sonnet 검수 → research/newsletter_{ID}_{YYYYMMDD}_final.md
  4. newsletter_notion.py   — Notion DB에 최종본 업로드 (NOTION_API_KEY 없으면 건너뜀)
```
Gmail SMTP 자동 발송: A는 05:59, B는 06:00에 `newsletter_send.py`가 자동 실행.

> **주의**: `docker/crontab`의 "Resend 발송" 주석은 레거시 레이블로, 실제 구현은 Gmail SMTP (`GMAIL_USER` + `GMAIL_APP_PASSWORD` 환경변수)를 사용함.

**뉴스레터 구분**
- A: 글로벌 정치경제 — 매일 04:50 자동 실행, 05:59 Gmail 자동 발송
- B: AI 트렌드 — 매일 05:00 자동 실행, 06:00 Gmail 자동 발송

**설정 파일**: `data/newsletter_config_{A|B}.json` — 구독자 목록·RSS 소스·템플릿 등 뉴스레터별 설정.

---

## 데이터 파일 관리 (`data/`)

| 유형 | 패턴 | 설명 |
|------|------|------|
| 영구 | `marketcap-YYYY-MM-DD.json` | 일별 시총 스냅샷 (누적) |
| 영구 | `index.json` | 수집 날짜 목록 인덱스 |
| 영구 | `watchlist.json` | 워치리스트 (`{ticker, name, added_at}[]`) |
| 영구 | `target_portfolio.json` | 목표 포트폴리오 설정 |
| 영구 | `newsletter_config_{A\|B}.json` | 뉴스레터 설정 |
| 캐시 | `kr_stocks_cache.json` | 한국 종목 티커 캐시 (24h TTL) |
| 임시 | `_temp_newsletter_{A\|B}.json` | 뉴스레터 수집 단계 결과물 |
| 임시 | `_stibee_*.json` | Stibee API 응답 디버그용 (수동 정리) |
| 런타임 | `_alerted.json` | 실시간 급변 알림 완료 티커 (봇 재시작 시 복원용, 자정 초기화) |

`output/` 폴더 — 자동 삭제되지 않음, 수동 정리 필요:
- `_temp_TICKER.json` — stock-agent 파이프라인 중간 결과물
- `TICKER_YYYYMMDD.xlsx` — 개별 종목 리서치 리포트
- `portfolio_master.xlsx` — 누적 포트폴리오 마스터 (실행마다 갱신)
- `portfolio_status_YYYYMMDD_HHmm.xlsx` — portfolio-analyzer 출력

`research/` 폴더 — 마크다운 리서치 파일 (git tracked):
- `TICKER_YYYYMMDD.md` — stock-agent 리서치 결과
- `newsletter_{A|B}_{YYYYMMDD}.md` — 뉴스레터 AI 초안
- `newsletter_{A|B}_{YYYYMMDD}_final.md` — 뉴스레터 최종본 (검수 완료)

`Public/` — 개인 참조 문서(북마크 HTML, notion 체크리스트 등). 코드와 무관, git untracked 상태 유지.
