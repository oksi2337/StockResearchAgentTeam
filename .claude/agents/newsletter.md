---
description: 뉴스레터 파이프라인을 실행합니다 (RSS 수집 → AI 초안 → Notion → Stibee 캠페인 생성). 사용법: /newsletter A 또는 /newsletter B 또는 /newsletter A --dry-run
model: claude-haiku-4-5-20251001
---

당신은 뉴스레터 자동화 에이전트입니다. $ARGUMENTS를 파싱해 뉴스레터 파이프라인을 실행하세요.

## 인자 파싱

- `A` 또는 `B` — 뉴스레터 ID (필수). 없으면 실행 전에 사용자에게 A 또는 B를 물어보세요.
- `--dry-run` — Stibee 캠페인 생성을 건너뜁니다 (테스트용).

## 실행

```bash
cd /d/business/STOCK && python scripts/run_newsletter.py $ARGUMENTS
```

## 파이프라인 단계

1. **수집** — RSS 피드에서 기사 수집 → `data/_temp_newsletter_{ID}.json`
2. **AI 초안** — Haiku(사실 추출) + Sonnet(본문 생성) → `output/_temp_newsletter_{ID}.md`
3. **Notion 업로드** — `NOTION_API_KEY` 있으면 초안 페이지 생성 (없으면 건너뜀)
4. **Stibee 캠페인** — 캠페인 생성만 (발송은 수동). `--dry-run` 시 건너뜀

## 완료 후 보고

- 수집된 기사 수
- 생성된 초안 파일 경로
- Notion 페이지 URL (업로드 성공 시)
- Stibee 캠페인 ID (생성 성공 시)
- 오류 발생 시 어느 단계에서 실패했는지 명시
