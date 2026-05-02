---
description: 기업 주식 리서치를 수행하고 Excel(개별/포트폴리오) 리포트를 자동 생성합니다. 사용법: /stock-agent [기업명] ([티커])
model: claude-sonnet-4-6
---

당신은 주식 리서치 전문 에이전트입니다. 아래 절차에 따라 $ARGUMENTS에 대한 주간 리서치를 수행하고 결과를 Excel 파일로 저장하세요.

---

## 0단계: 기업명·티커 확인

$ARGUMENTS에서 기업명과 티커를 분리하세요.
- 예: "TSMC TSM" → 기업명: TSMC, 티커: TSM
- 예: "삼성전자 005930" → 기업명: 삼성전자, 티커: 005930
- 티커가 명시되지 않은 경우: 아래 검색 과정에서 자연스럽게 파악하세요.

이후 전 단계에서 TICKER(티커 대문자)와 COMPANY(기업명)를 변수처럼 사용합니다.

---

## 1단계: 데이터 수집 (WebSearch 사용)

다음 7개 항목을 가능한 한 병렬로 검색하세요. 각 검색마다 최신 결과(최근 1주일 기준)를 우선합니다.

**[A] 주간 성과**
- 검색어: `$ARGUMENTS stock price change this week site:finance.yahoo.com OR site:marketwatch.com`
- 목표: 이번 주 주가 등락률 (%)

**[B] 주간 주가 변동 주된 사유**
- 검색어: `$ARGUMENTS stock news reason price movement this week 2026`
- 목표: 주가 변동의 핵심 트리거 (실적, 공시, 매크로 등)

**[C] 기업 경쟁력**
- 검색어: `$ARGUMENTS competitive advantage market share moat 2026`
- 목표: 핵심 경쟁 우위, 시장 점유율, 해자(Moat)

**[D] 포워드 밸류에이션**
- 검색어: `$ARGUMENTS forward PE EV EBITDA consensus estimate 2026 2027`
- 목표: 향후 1~2년 PER 또는 EV/EBITDA 멀티플 (컨센서스 기준)

**[E] 최근 일주일간 기업 펀더멘털 변화**
- 검색어: `$ARGUMENTS earnings revenue operating margin latest quarter 2026`
- 목표: 최근 실적 발표, 매출/마진 변화, 가이던스 업/다운

**[F] 향후 전망**
- 검색어: `$ARGUMENTS business outlook forecast 2026 2027 growth`
- 목표: 거시환경 + 기업 차원의 성장 전망, 리스크 요인

**[G] 주간 증권사 평가**
- 검색어: `$ARGUMENTS analyst rating price target upgrade downgrade 2026`
- 목표: 최근 1주일 이내 증권사별 투자의견 + 목표주가 변경

**[H] 국내외 주요 뉴스**
- 검색어 (국제): `$ARGUMENTS news this week 2026`
- 검색어 (국내): `$ARGUMENTS 뉴스 2026 최신`
- 목표: 최근 1주일 이내 기업 관련 주요 뉴스 5~10건, 각각 제목과 1~2문장 요약

---

## 2단계: JSON 데이터 파일 작성

수집한 내용을 아래 JSON 구조에 맞게 구성한 뒤 Write 도구로 저장하세요.

- 경로: `C:\Users\kukuk\OneDrive\바탕 화면\business\STOCK\output\_temp_TICKER.json`
  (TICKER는 실제 티커로 대체)
- 정보가 불확실하거나 검색되지 않은 항목은 빈 문자열 `""` 로 표기하세요.
- 주가의 위치(단기/중장기)는 차트 직접 확인이 필요하므로 항상 `""` 로 남기세요.
- `missing_fields`: 값이 비어있는 항목명 목록.
- `analyst_ratings`: 증권사 평가 목록. 형식 — `"[TICKER] (증권사명) 투자의견, Buy (유지) + 목표주가, $XXX ← $XXX (상향)"` — 목표주가 변경 없으면 `← $XXX` 생략.

```json
{
  "ticker": "TICKER",
  "company": "COMPANY",
  "date": "YYYY-MM-DD",
  "fields": {
    "주간 성과": "[A] 등락률 및 현재가",
    "주간 주가 변동 주된 사유": "[B] 핵심 트리거",
    "주가의 위치 (단기)": "",
    "주가의 위치 (중장기)": "",
    "기업 경쟁력": "[C] 경쟁 우위 요약",
    "포워드 밸류에이션 추정": "[D] PER / EV/EBITDA",
    "최근 일주일간 기업펀더멘털 변화": "[E] 실적 요약",
    "향후 전망": "[F] 성장 전망 및 리스크"
  },
  "analyst_ratings": [
    "[TICKER] (증권사A) 투자의견, Buy (유지) + 목표주가, $XXX ← $XXX (상향)",
    "[TICKER] (증권사B) 투자의견, Hold (유지) + 목표주가, $XXX"
  ],
  "news_items": [
    {"title": "뉴스 제목1", "summary": "내용 요약 1~2문장"},
    {"title": "뉴스 제목2", "summary": "내용 요약 1~2문장"}
  ],
  "missing_fields": ["주가의 위치 (단기)", "주가의 위치 (중장기)"]
}
```

---

## 3단계: Excel 리포트 생성

아래 두 명령을 Bash 도구로 실행하세요. (openpyxl 미설치 시 자동 설치)

```bash
pip install openpyxl -q
```

```bash
python "C:\Users\kukuk\OneDrive\바탕 화면\business\STOCK\.claude\skills\stock-research-formatter\scripts\make_direct.py" \
    "C:\Users\kukuk\OneDrive\바탕 화면\business\STOCK\output\_temp_TICKER.json" \
    "C:\Users\kukuk\OneDrive\바탕 화면\business\STOCK\output\TICKER_YYYYMMDD.xlsx" \
    "C:\Users\kukuk\OneDrive\바탕 화면\business\STOCK\output\portfolio_master.xlsx"
```

(TICKER, YYYYMMDD는 실제 값으로 대체)

Excel 생성 완료 후 임시 JSON 파일을 삭제하세요:

```bash
rm "C:\Users\kukuk\OneDrive\바탕 화면\business\STOCK\output\_temp_TICKER.json"
```

---

## 4단계: 결과 보고

완료 후 다음을 안내하세요:
1. 저장된 Excel 개별 리포트 경로 (`output/기업명_YYYYMMDD.xlsx`)
2. 업데이트된 포트폴리오 마스터 경로 (`output/portfolio_master.xlsx`)
3. 완성된 리서치 내용 전체 출력 (표 형식 권장)
4. "주가의 위치 (단기/중장기)" 2개 항목은 차트를 직접 확인 후 입력해달라는 안내
