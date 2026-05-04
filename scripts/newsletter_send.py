"""
newsletter_send.py — Stibee 구독자 목록 + Gmail SMTP로 뉴스레터 발송
사용법: python scripts/newsletter_send.py [A|B]
"""
import os
import sys
import json
import time
import smtplib
import re
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

RESEARCH_DIR = ROOT / "research"
DATA_DIR = ROOT / "data"
KST = timezone(timedelta(hours=9))

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
STIBEE_API_KEY = os.getenv("STIBEE_API_KEY")
FROM_NAME_DEFAULT = "주키로그"


def get_subscribers(list_id: str) -> list[str]:
    """Stibee에서 subscribed 상태 구독자 이메일 목록 반환."""
    emails = []
    offset = 0
    limit = 100
    while True:
        resp = requests.get(
            f"https://api.stibee.com/v2/lists/{list_id}/subscribers?limit={limit}&offset={offset}",
            headers={"AccessToken": STIBEE_API_KEY},
            timeout=15,
        )
        resp.raise_for_status()
        items = resp.json()
        if not items:
            break
        for item in items:
            if item.get("status") == "subscribed":
                emails.append(item["email"])
        if len(items) < limit:
            break
        offset += limit
    return emails


def load_newsletter_md(newsletter_id: str) -> str:
    """오늘 날짜 _final.md 로드. 없으면 _final 없는 버전 시도."""
    date_str = datetime.now(KST).strftime("%Y%m%d")
    for suffix in [f"_{date_str}_final.md", f"_{date_str}.md"]:
        path = RESEARCH_DIR / f"newsletter_{newsletter_id}{suffix}"
        if path.exists():
            return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"오늘({date_str}) 뉴스레터 {newsletter_id} 파일 없음")


def md_to_html(md: str, newsletter_name: str) -> str:
    """마크다운 → 이메일용 HTML."""

    def _inline(text: str) -> str:
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" style="color:#0066cc">\1</a>', text)
        return text

    def _table_row(line: str) -> str:
        if re.match(r"^\|[-| ]+\|$", line):
            return ""
        cells = [c.strip() for c in line.strip("|").split("|")]
        return "<tr>" + "".join(f"<td style='padding:6px 12px;border:1px solid #eee'>{c}</td>" for c in cells) + "</tr>"

    parts = [
        "<!DOCTYPE html><html lang='ko'><head><meta charset='UTF-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
        f"<title>{newsletter_name}</title></head>",
        "<body style='margin:0;padding:0;background:#f5f5f5;font-family:sans-serif'>",
        "<table width='100%' cellpadding='0' cellspacing='0'>",
        "<tr><td align='center'><table width='600' style='background:#ffffff;padding:32px'>",
    ]

    skip_header = True
    for line in md.splitlines():
        s = line.strip()
        if skip_header:
            if s.startswith("---"):
                skip_header = False
            continue
        if not s:
            parts.append("<br>")
        elif s.startswith("# "):
            parts.append(f"<h1 style='font-size:22px;color:#1a1a1a;margin:0 0 8px'>{s[2:]}</h1>")
        elif s.startswith("## "):
            parts.append(f"<h2 style='font-size:18px;color:#1a1a1a;border-bottom:2px solid #333;padding-bottom:6px;margin:24px 0 12px'>{s[3:]}</h2>")
        elif s.startswith("**") and s.endswith("**"):
            parts.append(f"<p style='font-weight:bold;color:#333;margin:12px 0 4px'>{s.strip('*')}</p>")
        elif s.startswith("> "):
            parts.append(f"<blockquote style='border-left:4px solid #555;padding:8px 16px;margin:16px 0;background:#f9f9f9;color:#444;font-style:italic'>{s[2:]}</blockquote>")
        elif s.startswith("- ") or s.startswith("* "):
            parts.append(f"<li style='margin:4px 0;color:#333'>{_inline(s[2:])}</li>")
        elif re.match(r"^\d+\. ", s):
            parts.append(f"<li style='margin:4px 0;color:#333'>{_inline(re.sub(r'^\d+\. ', '', s))}</li>")
        elif s.startswith("---"):
            parts.append("<hr style='border:none;border-top:1px solid #eee;margin:20px 0'>")
        elif s.startswith("_") and s.endswith("_"):
            parts.append(f"<p style='font-size:12px;color:#888;margin:4px 0'>{s.strip('_')}</p>")
        elif s.startswith("|"):
            parts.append(_table_row(s))
        else:
            parts.append(f"<p style='color:#333;line-height:1.7;margin:8px 0'>{_inline(s)}</p>")

    parts += [
        "<tr><td style='height:24px'></td></tr>",
        "<tr><td style='font-size:12px;color:#aaa;text-align:center;padding-top:16px;border-top:1px solid #eee'>",
        "이 메일은 주키로그 뉴스레터 구독자에게 발송됩니다.",
        "</td></tr>",
        "</table></td></tr></table></body></html>",
    ]
    return "\n".join(parts)


def send_via_gmail(subscribers: list[str], subject: str, html: str, from_name: str) -> tuple[int, int]:
    """Gmail SMTP로 구독자 전체 발송. (성공수, 실패수) 반환."""
    success, fail = 0, 0
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        for email in subscribers:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{from_name} <{GMAIL_USER}>"
                msg["To"] = email
                msg.attach(MIMEText(html, "html", "utf-8"))
                smtp.sendmail(GMAIL_USER, email, msg.as_bytes())
                success += 1
            except Exception as e:
                fail += 1
                print(f"  [실패] {email}: {e}")
            time.sleep(0.1)
    return success, fail


def run(newsletter_id: str) -> None:
    config = json.loads((DATA_DIR / f"newsletter_config_{newsletter_id}.json").read_text(encoding="utf-8"))
    list_id_env = config.get("stibee_list_id_env", f"STIBEE_LIST_ID_{newsletter_id}")
    list_id = os.getenv(list_id_env)
    if not list_id:
        raise EnvironmentError(f"환경변수 없음: {list_id_env}")

    from_name = config.get("sender_name", FROM_NAME_DEFAULT)
    newsletter_name = config["name"]
    date_str = datetime.now(KST).strftime("%Y-%m-%d")
    subject = f"{newsletter_name} - {date_str}"

    print(f"\n[발송] 뉴스레터 {newsletter_id}: {subject}")

    md = load_newsletter_md(newsletter_id)
    html = md_to_html(md, newsletter_name)

    print("[구독자] Stibee 목록 조회 중...")
    subscribers = get_subscribers(list_id)
    print(f"[구독자] {len(subscribers)}명 (subscribed 상태)")

    if not subscribers:
        print("[발송] 구독자 없음 - 건너뜀")
        return

    success, fail = send_via_gmail(subscribers, subject, html, from_name)
    print(f"[완료] 성공 {success}명 / 실패 {fail}명")


if __name__ == "__main__":
    nid = sys.argv[1].upper() if len(sys.argv) > 1 else "A"
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("[오류] GMAIL_USER 또는 GMAIL_APP_PASSWORD 없음")
        sys.exit(1)
    run(nid)
