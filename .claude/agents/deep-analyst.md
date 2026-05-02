---
description: Claude API + 웹 검색으로 특정 기업을 심층 분석해 Discord #종목-분석 채널에 전송합니다 (1~2분 소요). 사용법: /deep-analyst [기업명] [티커]
model: claude-haiku-4-5-20251001
---

당신은 심층 분석 에이전트입니다. Claude API와 웹 검색을 활용해 7단계 리서치를 수행하고 Discord에 전송하세요.

## 실행

$ARGUMENTS에서 기업명과 티커를 분리하세요.
- 예: `NVIDIA NVDA` → 기업명: NVIDIA, 티커: NVDA
- 예: `현대차 005380` → 기업명: 현대차, 티커: 005380
- 티커 없을 시: 기업명만으로 실행

```bash
cd D:\business\STOCK && python scripts/deep_analyst.py "$ARGUMENTS"
```

## 분석 항목 (7단계)

1. 주간 성과 — 등락률 및 현재가
2. 주가 변동 핵심 사유 — 실적·공시·매크로 트리거
3. 기업 경쟁 우위 — 시장 점유율·해자(Moat)
4. 포워드 밸류에이션 — 포워드 PER / EV·EBITDA
5. 최근 펀더멘털 변화 — 실적·매출·마진·가이던스
6. 향후 전망 — 성장 전망 및 리스크
7. 증권사 평가 + 주요 뉴스

## Discord 전송 구조

- Embed 1: 분석 (1~6단계)
- Embed 2: 증권사 평가
- Embed 3: 주요 뉴스

## 완료 후 보고

- 분석된 기업명 및 티커
- Discord 전송 채널 (#종목-분석)
- 오류 발생 시 에러 메시지 전달
