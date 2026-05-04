---
description: 뉴스레터 파이프라인을 실행합니다 (RSS 수집 → AI 초안 → Notion 업로드). 사용법: /newsletter A 또는 /newsletter B
model: claude-haiku-4-5-20251001
---

당신은 뉴스레터 자동화 에이전트입니다.

`$ARGUMENTS`에서 뉴스레터 ID(A 또는 B)를 파악한 뒤, 아래 명령을 Bash 도구로 실행하세요:

```bash
cd D:\business\STOCK && python scripts/run_newsletter.py $ARGUMENTS
```

인자가 없으면 기본값 A로 실행합니다.

## 파이프라인 단계

1. **수집** — RSS 피드에서 기사 수집 → `data/_temp_newsletter_{ID}.json`
2. **AI 초안** — Haiku(사실 추출) + Sonnet(본문 생성) → `research/newsletter_{ID}_{YYYYMMDD}.md`
3. **Notion 업로드** — `NOTION_API_KEY` 있으면 초안 페이지 생성 (없으면 건너뜀)

## 완료 후 보고

- 수집된 기사 수
- 생성된 초안 파일 경로 (`research/newsletter_*.md`)
- Notion 페이지 URL (업로드 성공 시)
- 오류 발생 시 어느 단계에서 실패했는지 명시
