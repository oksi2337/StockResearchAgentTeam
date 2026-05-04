"""
run_newsletter.py — 뉴스레터 전체 파이프라인 오케스트레이터
사용법: python scripts/run_newsletter.py [A|B] [--dry-run]

단계:
  1. newsletter_collect  — RSS 수집 + 시장 데이터
  2. newsletter_ai       — Haiku 사실 추출 + Sonnet 본문 생성
  3. newsletter_notion   — Notion 초안 페이지 업로드
  4. newsletter_stibee   — Stibee 캠페인 생성 (발송은 수동)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main():
    args = sys.argv[1:]
    nid = "A"
    dry_run = False

    for arg in args:
        if arg.upper() in ("A", "B"):
            nid = arg.upper()
        elif arg == "--dry-run":
            dry_run = True

    print(f"\n{'='*60}")
    print(f"  뉴스레터 {nid} 파이프라인 시작 (dry_run={dry_run})")
    print(f"{'='*60}\n")

    # ── 1단계: 수집 ─────────────────────────────────────────────
    try:
        from newsletter_collect import run as collect
        collect(nid)
    except Exception as e:
        print(f"\n[오류] 수집 실패: {e}")
        print("파이프라인 중단.")
        sys.exit(1)

    time.sleep(2)

    # ── 2단계: AI 초안 생성 ─────────────────────────────────────
    try:
        from newsletter_ai import run as ai_draft
        md_path = ai_draft(nid)
        print(f"\n초안 파일: {md_path}")
    except Exception as e:
        print(f"\n[오류] AI 초안 생성 실패: {e}")
        print("파이프라인 중단.")
        sys.exit(1)

    time.sleep(2)

    # ── 3단계: Notion 업로드 ────────────────────────────────────
    notion_url = None
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

        if os.getenv("NOTION_API_KEY"):
            from newsletter_notion import run as notion_upload
            notion_url = notion_upload(nid)
        else:
            print("\n[Notion] NOTION_API_KEY 없음 - 업로드 건너뜀")
    except Exception as e:
        print(f"\n[경고] Notion 업로드 실패 (발송은 계속): {e}")

    time.sleep(2)

    print("\n[안내] Notion 초안 검수 후 직접 발송하세요.")

    # ── 완료 ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  뉴스레터 {nid} 파이프라인 완료")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()