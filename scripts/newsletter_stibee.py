"""
newsletter_stibee.py — 뉴스레터 초안을 HTML로 변환 후 Stibee API로 발송
Stibee API 문서: https://help.stibee.com/hc/ko/articles/4756388938511
"""
import os
import sys
import json
import re
import time
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

DATA_DIR = ROOT / "data"
RESEARCH_DIR = ROOT / "research"
KST = timezone(timedelta(hours=9))

STIBEE_API = "https://api.stibee.com/v2"
STIBEE_API_KEY = os.getenv("STIBEE_API_KEY")


def md_to_html(md: str, newsletter_name: str) -> str:
    """마크다운 → 이메일용 HTML (인라인 스타일 적용)."""
    html_parts = [
        "<!DOCTYPE html><html lang='ko'><head><meta charset='UTF-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"<title>{newsletter_name}</title></head>",
        "<body style='margin:0;padding:0;background:#f5f5f5;font-family:sans-serif'>",
        "<table width='100%' cellpadding='0' cellspacing='0'>",
        "<tr><td align='center'><table width='600' style='background:#ffffff;padding:32px'>",
    ]

    skip_header = True
    for line in md.splitlines():
        stripped = line.strip()

        if skip_header and stripped.startswith("---"):
            skip_header = False
            continue
        if skip_header:
            continue

        if not stripped:
            html_parts.append("<br>")
        elif stripped.startswith("# "):
            html_parts.append(
                f"<h1 style='font-size:22px;color:#1a1a1a;margin:0 0 8px'>{stripped[2:]}</h1>"
            )
        elif stripped.startswith("## "):
            title = stripped[3:]
            html_parts.append(
                f"<h2 style='font-size:18px;color:#1a1a1a;border-bottom:2px solid #333;padding-bottom:6px;margin:24px 0 12px'>{title}</h2>"
            )
        elif stripped.startswith("**") and stripped.endswith("**"):
            html_parts.append(
                f"<p style='font-weight:bold;color:#333;margin:12px 0 4px'>{stripped.strip('*')}</p>"
            )
        elif stripped.startswith("> "):
            html_parts.append(
                f"<blockquote style='border-left:4px solid #555;padding:8px 16px;margin:16px 0;background:#f9f9f9;color:#444;font-style:italic'>{stripped[2:]}</blockquote>"
            )
        elif stripped.startswith("- ") or stripped.startswith("* "):
            html_parts.append(
                f"<li style='margin:4px 0;color:#333'>{_inline_md(stripped[2:])}</li>"
            )
        elif re.match(r"^\d+\. ", stripped):
            content = re.sub(r"^\d+\. ", "", stripped)
            html_parts.append(
                f"<li style='margin:4px 0;color:#333'>{_inline_md(content)}</li>"
            )
        elif stripped.startswith("---"):
            html_parts.append("<hr style='border:none;border-top:1px solid #eee;margin:20px 0'>")
        elif stripped.startswith("_") and stripped.endswith("_"):
            html_parts.append(
                f"<p style='font-size:12px;color:#888;margin:4px 0'>{stripped.strip('_')}</p>"
            )
        elif stripped.startswith("|"):
            html_parts.append(_table_row(stripped))
        else:
            html_parts.append(
                f"<p style='color:#333;line-height:1.7;margin:8px 0'>{_inline_md(stripped)}</p>"
            )

    html_parts += [
        "<tr><td style='height:24px'></td></tr>",
        "<tr><td style='font-size:12px;color:#aaa;text-align:center;padding-top:16px;border-top:1px solid #eee'>",
        "구독을 원하지 않으시면 <a href='{{unsubscribe}}' style='color:#aaa'>수신 거부</a>하세요.",
        "</td></tr>",
        "</table></td></tr></table></body></html>",
    ]
    return "\n".join(html_parts)


def _inline_md(text: str) -> str:
    """인라인 마크다운(볼드, 이탤릭, 링크) → HTML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" style="color:#0066cc">\1</a>', text)
    return text


def _table_row(line: str) -> str:
    """마크다운 테이블 행 → HTML."""
    if re.match(r"^\|[-| ]+\|$", line):
        return ""
    cells = [c.strip() for c in line.strip("|").split("|")]
    cells_html = "".join(f"<td style='padding:6px 12px;border:1px solid #eee'>{c}</td>" for c in cells)
    return f"<tr>{cells_html}</tr>"


def _get_list_id(config: dict) -> str:
    env_key = config.get("stibee_list_id_env", "STIBEE_LIST_ID_A")
    list_id = os.getenv(env_key)
    if not list_id:
        raise EnvironmentError(f"환경변수 없음: {env_key}")
    return list_id


def create_campaign(list_id: str, subject: str, html_content: str, send_time: str) -> str:
    """Stibee API로 캠페인 생성. 캠페인 ID 반환."""
    headers = {
        "AccessToken": STIBEE_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "addressBookId": list_id,
        "subject": subject,
        "contents": html_content,
        "sendType": "scheduled",
        "scheduledAt": send_time,
    }
    resp = requests.post(
        f"{STIBEE_API}/emails",
        headers=headers,
        json=payload,
        timeout=30,
    )
    if not resp.ok:
        try:
            print(f"[Stibee] 오류 응답: {resp.status_code} {resp.text[:500]}")
        except Exception:
            pass
    resp.raise_for_status()
    data = resp.json()
    campaign_id = data.get("id") or data.get("emailId", "")
    print(f"[Stibee] 캠페인 생성: ID={campaign_id}")
    return str(campaign_id)


def schedule_send(campaign_id: str) -> None:
    """생성된 캠페인 발송 예약 확정."""
    headers = {"AccessToken": STIBEE_API_KEY, "Content-Type": "application/json"}
    resp = requests.post(
        f"{STIBEE_API}/campaigns/{campaign_id}/send",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    print(f"[Stibee] 발송 예약 완료: {campaign_id}")


def run(newsletter_id: str, dry_run: bool = False) -> None:
    if not STIBEE_API_KEY and not dry_run:
        print("[Stibee] STIBEE_API_KEY 없음 - 발송 건너뜀 (Notion 검수 후 수동 발송하세요)")
        return

    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    date_compact = date_str.replace("-", "")
    md_path = RESEARCH_DIR / f"newsletter_{newsletter_id}_{date_compact}.md"

    if not md_path.exists():
        raise FileNotFoundError(f"초안 파일 없음: {md_path}")

    config = json.loads((DATA_DIR / f"newsletter_config_{newsletter_id}.json").read_text(encoding="utf-8"))
    md_text = md_path.read_text(encoding="utf-8")
    html = md_to_html(md_text, config["name"])

    send_time_str = config["schedule"]["send_time"]
    send_datetime = f"{date_str}T{send_time_str}:00+09:00"
    subject = f"{config['name']} - {date_str}"

    print(f"\n[Stibee] newsletter {newsletter_id} send prep")
    print(f"  subject: {subject}")
    print(f"  scheduled: {send_datetime}")

    if dry_run:
        html_path = RESEARCH_DIR / f"newsletter_{newsletter_id}_{date_compact}.html"
        html_path.write_text(html, encoding="utf-8")
        print(f"[Dry-run] HTML saved: {html_path}")
        return

    list_id = _get_list_id(config)
    for attempt in range(1, 4):
        try:
            campaign_id = create_campaign(list_id, subject, html, send_datetime)
            time.sleep(1)
            # schedule_send(campaign_id)  # [수동 검수] 발송은 Stibee에서 수동으로
            print(f"[Stibee] 캠페인 생성 완료 - ID: {campaign_id}")
            return
        except Exception as e:
            print(f"[Stibee] 시도 {attempt}/3 실패: {e}")
            if attempt < 3:
                time.sleep(10)

    print("[Stibee] 발송 실패 -- Notion 초안에서 수동 발송하세요")


if __name__ == "__main__":
    nid = sys.argv[1].upper() if len(sys.argv) > 1 else "A"
    dry = "--dry-run" in sys.argv
    run(nid, dry_run=dry)
