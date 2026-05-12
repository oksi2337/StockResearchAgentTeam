# PC 포맷 후 복구 가이드

> NAS 컨테이너(Discord 봇, 자동 리포트, 뉴스레터)는 PC와 무관하게 계속 실행됨.
> 이 문서는 **PC 개발 환경** 복구 절차만 다룸.

---

## 1. 포맷 전 필수 백업

아래 항목은 git에 없으므로 반드시 따로 보관.

| 항목 | 경로 | 비고 |
|------|------|------|
| 환경변수 | `D:\business\STOCK\.env` | API 키 전부 포함, 최우선 백업 |
| 목표 포트폴리오 | `data\target_portfolio.json` | portfolio-analyzer 설정 |
| 워치리스트 | `data\watchlist.json` | NAS 버전이 더 최신일 수 있음 |
| Excel 리포트 | `output\` 폴더 전체 | 자동 삭제 안 됨 |
| 리서치 MD | `research\` 폴더 전체 | stock-agent 결과물 |

미커밋 코드 확인:
```powershell
git status
git diff
```

---

## 2. 설치할 소프트웨어

### 필수

| 소프트웨어 | 버전 | 용도 |
|-----------|------|------|
| **Git** | 최신 | 저장소 클론 및 버전 관리 |
| **Node.js** | 20 LTS 이상 | 시총 대시보드 (React + Express) |
| **Python** | 3.12 | Discord 봇, 자동화 스크립트 전체 |
| **Claude Code** | 최신 | `/stock-agent`, `/portfolio-analyzer` 등 슬래시 커맨드 |

### 선택

| 소프트웨어 | 용도 |
|-----------|------|
| **WinSCP** | NAS에 스크립트 업로드 (SFTP) |
| **Docker Desktop** | 로컬 PC에서 봇 컨테이너 테스트할 때만 필요 |

---

## 3. 설치 순서

### 3-1. Git
```
https://git-scm.com/download/win
```

### 3-2. Node.js
```
https://nodejs.org/  (LTS 버전)
```

### 3-3. Python 3.12
```
https://www.python.org/downloads/
```
설치 시 **"Add Python to PATH"** 체크 필수.

### 3-4. Claude Code
```powershell
npm install -g @anthropic-ai/claude-code
```

---

## 4. 프로젝트 복구

### 4-1. 저장소 클론
```powershell
git clone <remote-url> D:\business\STOCK
cd D:\business\STOCK
```

### 4-2. `.env` 파일 복원
백업해둔 `.env`를 `D:\business\STOCK\.env`에 복사.
없으면 `.env.example`을 복사 후 값 입력:
```powershell
Copy-Item .env.example .env
# 메모장 등으로 열어 API 키 입력
```

### 4-3. Node.js 의존성 설치 (대시보드)
```powershell
npm install
```

### 4-4. Python 의존성 설치 (봇·자동화)
```powershell
pip install -r requirements.txt
pip install openpyxl          # Excel 생성 (requirements.txt 미포함)
```

---

## 5. 동작 확인

### 대시보드
```powershell
npm run dev
# 브라우저에서 http://localhost:5173 접속
```

### Discord 봇 (수동 테스트)
```powershell
python scripts/discord_bot.py
# NAS 봇과 동시 실행 금지 — 테스트 후 바로 종료
```

### 뉴스레터 파이프라인 테스트
```powershell
python scripts/run_newsletter.py A
```

### stock-agent / portfolio-analyzer (Claude Code)
```powershell
claude
# Claude Code 내에서
# /stock-agent NVIDIA NVDA
# /portfolio-analyzer
```

---

## 6. NAS — 포맷 후 할 일 없음

NAS 컨테이너는 독립 실행 중이므로 별도 작업 불필요.

새 스크립트를 `scripts/`에 추가했을 경우에만 WinSCP로 업로드:
```
로컬: D:\business\STOCK\scripts\새파일.py
NAS:  /volume1/docker/stock/scripts/새파일.py
```
업로드 후 컨테이너 재시작 불필요 (볼륨 마운트로 즉시 반영).
`docker/`, `requirements.txt` 변경 시에는 NAS에서 이미지 재빌드 필요.

---

## 7. Windows Task Scheduler (필요 시만)

뉴스레터 A/B는 NAS cron이 이미 담당하므로 **재등록 불필요**.
만약 PC에서도 돌리려면 (NAS와 중복 전송 발생 주의):

```powershell
# 관리자 PowerShell로 실행
.\scripts\setup_scheduler.ps1
# 등록 후 DailyReport / KoreanMarket / DiscordBot 태스크는 비활성화 상태로 유지
```
