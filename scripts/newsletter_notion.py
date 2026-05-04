"""
newsletter_notion.py — 뉴스레터 초안을 Notion 페이지로 업로드
구조: 섹션별 토글 블록 + 상단 검수 안내 콜아웃
"""
import os
import sys
import re
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from notion_client import Client
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

DATA_DIR = ROOT / "data"
RESEARCH_DIR = ROOT / "research"
KST = timezone(timedelta(hours=9))

notion = Client(auth=os.getenv("NOTION_API_KEY"))


def _get_db_id(config: dict) -> str:
    env_key = config.get("notion_database_id_env", "NOTION_DATABASE_ID")
    db_id = os.getenv(env_key)
    if not db_id:
        raise EnvironmentError(f"환경변수 없음: {env_key}")
    return db_id


def _parse_rich_text(text: str) -> list[dict]:
    """마크다운 [텍스트](url) 링크와 **bold** → Notion rich_text 배열로 변환."""
    result = []
    pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*')
    last_end = 0
    for m in pattern.finditer(text):
        if m.start() > last_end:
            result.append({"type": "text", "text": {"content": text[last_end:m.start()][:2000]}})
        if m.group(1) is not None:
            result.append({"type": "text", "text": {"content": m.group(1)[:2000], "link": {"url": m.group(2)}}})
        else:
            result.append({"type": "text", "text": {"content": m.group(3)[:2000]}})
        last_end = m.end()
    if last_end < len(text):
        result.append({"type": "text", "text": {"content": text[last_end:][:2000]}})
    return result or [{"type": "text", "text": {"content": text[:2000]}}]


def _text(content: str) -> dict:
    return {"type": "text", "text": {"content": content[:2000]}}


def _paragraph(text: str) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": _parse_rich_text(text)}}


def _heading2(text: str) -> dict:
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": _parse_rich_text(text)}}


def _callout(text: str, emoji: str = "⚠️") -> dict:
    return {
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [_text(text)],
            "icon": {"type": "emoji", "emoji": emoji},
            "color": "yellow_background",
        }
    }


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _toggle(title: str, children: list[dict]) -> dict:
    return {
        "object": "block", "type": "toggle",
        "toggle": {
            "rich_text": [_text(title)],
            "children": children[:100],
        }
    }


def _bullet(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": _parse_rich_text(text)}}


def parse_sections(md: str) -> dict[str, str]:
    """마크다운을 ## 섹션 단위로 분리."""
    sections: dict[str, str] = {}
    current_title = "header"
    current_lines: list[str] = []

    for line in md.splitlines():
        if line.startswith("## "):
            if current_lines:
                sections[current_title] = "\n".join(current_lines).strip()
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_title] = "\n".join(current_lines).strip()
    return sections


def md_section_to_blocks(text: str) -> list[dict]:
    """섹션 텍스트를 Notion 블록 목록으로 변환."""
    blocks = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            blocks.append(_bullet(stripped[2:]))
        elif re.match(r"^\d+\. ", stripped):
            blocks.append(_bullet(re.sub(r"^\d+\. ", "", stripped)))
        elif stripped.startswith("> "):
            blocks.append(_callout(stripped[2:], "💡"))
        elif stripped.startswith("**") and stripped.endswith("**"):
            blocks.append(_heading2(stripped.strip("*")))
        elif stripped.startswith("_출처:") or stripped.startswith("*출처:"):
            blocks.append(_paragraph(stripped.strip("_*")))
        elif stripped == "---":
            blocks.append(_divider())
        else:
            blocks.append(_paragraph(stripped))
    return blocks or [_paragraph("(내용 없음)")]


def build_page_blocks(sections: dict[str, str]) -> list[dict]:
    """전체 Notion 페이지 블록 구성."""
    blocks: list[dict] = []

    blocks.append(_callout(
        "⚠️ 표시 항목은 수치·고유명사를 원문 링크에서 직접 확인하세요. "
        "각 섹션 토글을 펼쳐서 편집 후 검수 완료 상태로 변경하세요.",
        "📋"
    ))
    blocks.append(_divider())

    for title, content in sections.items():
        if title == "header":
            continue
        children = md_section_to_blocks(content)
        blocks.append(_toggle(title, children))

    return blocks


def create_notion_page(config: dict, md_path: Path, date_str: str) -> str:
    """Notion 데이터베이스에 초안 페이지 생성. 페이지 URL 반환."""
    db_id = _get_db_id(config)
    md_text = md_path.read_text(encoding="utf-8")
    sections = parse_sections(md_text)

    page_title = f"[{config['id']}] {config['name']} — {date_str}"
    blocks = build_page_blocks(sections)

    # Notion API 블록 한 번에 최대 100개 → 첫 번째 create에 담을 수 있는 분량
    first_batch = blocks[:99]

    response = notion.pages.create(
        parent={"database_id": db_id},
        properties={
            "title": {"title": [{"text": {"content": page_title}}]},
        },
        children=first_batch,
    )
    page_id = response["id"]

    # 나머지 블록 추가
    if len(blocks) > 99:
        for i in range(99, len(blocks), 99):
            notion.blocks.children.append(
                block_id=page_id,
                children=blocks[i:i+99],
            )

    page_url = response.get("url", f"https://notion.so/{page_id.replace('-', '')}")
    print(f"[Notion] 페이지 생성: {page_url}")
    return page_url


def run(newsletter_id: str) -> str:
    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    date_compact = date_str.replace("-", "")

    md_path = RESEARCH_DIR / f"newsletter_{newsletter_id}_{date_compact}.md"
    if not md_path.exists():
        raise FileNotFoundError(f"초안 파일 없음: {md_path} (newsletter_ai.py 먼저 실행)")

    config = json.loads((DATA_DIR / f"newsletter_config_{newsletter_id}.json").read_text(encoding="utf-8"))

    print(f"\n[Notion] 뉴스레터 {newsletter_id} 초안 업로드...")
    page_url = create_notion_page(config, md_path, date_str)
    return page_url


if __name__ == "__main__":
    nid = sys.argv[1].upper() if len(sys.argv) > 1 else "A"
    url = run(nid)
    print(f"\n검수 링크: {url}")
