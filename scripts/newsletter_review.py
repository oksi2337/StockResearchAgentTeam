"""
newsletter_review.py — Claude Sonnet으로 뉴스레터 초안 검수
입력: research/newsletter_{ID}_{YYYYMMDD}.md
출력: research/newsletter_{ID}_{YYYYMMDD}_final.md
"""
import os
import sys
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

RESEARCH_DIR = ROOT / "research"
KST = timezone(timedelta(hours=9))

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
SONNET = "claude-sonnet-4-6"

REVIEW_SYSTEM = """당신은 한국어 뉴스레터 에디터입니다. 아래 초안을 검수해 수정된 전체 본문을 출력하세요.

검수 기준:
1. 포맷 교정
   - 링크는 반드시 [제목](url) 형식 — `([링크])` 또는 `(url)` 단독 형식 금지
   - 소제목 포함 **bold(`**`)** 사용 금지 — 평문으로 교정
   - 섹션 헤더(## 이모지 제목) 순서 유지

2. 문체 교정
   - '~습니다' 체 일관 유지
   - 번역투 어색한 문장 자연스러운 한국어로 교정
   - 지나치게 긴 문장(80자 초과) 분리 권장

3. ⚠️ 처리
   - 잘 알려진 기업명·인명(OpenAI, Google, 삼성전자 등) 앞 ⚠️ 제거
   - 원문 확인이 필요한 수치·비공개 고유명사 앞 ⚠️ 유지

4. 메타데이터 업데이트
   - `검수 상태: ⏳ 검수 전` → `검수 상태: ✅ Claude 검수 완료`

출력 규칙:
- 수정된 뉴스레터 마크다운 본문만 출력
- 설명, 주석, 추가 텍스트 절대 금지"""


def review_draft(draft: str, newsletter_id: str) -> str:
    print(f"[검수] Claude Sonnet 검수 시작... (뉴스레터 {newsletter_id})")
    response = client.messages.create(
        model=SONNET,
        max_tokens=8000,
        system=REVIEW_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"아래 뉴스레터 {newsletter_id} 초안을 검수하세요:\n\n{draft}"
        }]
    )
    return response.content[0].text.strip()


def run(newsletter_id: str) -> Path:
    date_compact = datetime.now(KST).strftime("%Y%m%d")
    draft_path = RESEARCH_DIR / f"newsletter_{newsletter_id}_{date_compact}.md"

    if not draft_path.exists():
        raise FileNotFoundError(f"초안 파일 없음: {draft_path} (newsletter_ai.py 먼저 실행)")

    draft = draft_path.read_text(encoding="utf-8")
    reviewed = review_draft(draft, newsletter_id)
    reviewed = reviewed.replace("⚠️", "").replace("⚠", "")

    out_path = RESEARCH_DIR / f"newsletter_{newsletter_id}_{date_compact}_final.md"
    out_path.write_text(reviewed, encoding="utf-8")
    print(f"[검수 완료] {out_path}")
    return out_path


if __name__ == "__main__":
    nid = sys.argv[1].upper() if len(sys.argv) > 1 else "A"
    path = run(nid)
    print(f"\n최종 파일: {path}")
