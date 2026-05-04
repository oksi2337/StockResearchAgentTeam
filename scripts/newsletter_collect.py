"""
newsletter_collect.py — RSS 수집 + 시장 데이터 수집
출력: data/_temp_newsletter_{A|B}.json
"""
import sys
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from html.parser import HTMLParser

import feedparser

sys.path.insert(0, str(Path(__file__).parent))
from yahoo_finance import get_intraday_change

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
KST = timezone(timedelta(hours=9))


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self):
        return " ".join(self._parts).strip()


def strip_html(html: str) -> str:
    if not html:
        return ""
    s = _HTMLStripper()
    try:
        s.feed(html)
        return re.sub(r"\s+", " ", s.get_text())
    except Exception:
        return re.sub(r"<[^>]+>", "", html).strip()


def fetch_rss(source: dict) -> list[dict]:
    """단일 RSS 피드 수집. 실패 시 빈 리스트 반환."""
    url = source["url"]
    max_items = source.get("max_items", 8)
    source_name = source["name"]
    try:
        feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
        articles = []
        for entry in feed.entries[:max_items]:
            title = strip_html(entry.get("title", "")).strip()
            summary = strip_html(
                entry.get("summary", "") or entry.get("description", "")
            )
            if len(summary) > 300:
                summary = summary[:300] + "…"
            url_link = entry.get("link", "")
            published = entry.get("published", "")
            if title:
                articles.append({
                    "source": source_name,
                    "title": title,
                    "summary": summary,
                    "url": url_link,
                    "published": published,
                })
        print(f"  [{source_name}] {len(articles)}개 수집")
        return articles
    except Exception as e:
        print(f"  [{source_name}] 수집 실패: {e}")
        return []


def fetch_all_rss(sources: list[dict]) -> list[dict]:
    """모든 소스 순차 수집 (중복 URL 제거)."""
    all_articles = []
    seen_urls = set()
    for source in sources:
        articles = fetch_rss(source)
        for article in articles:
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                all_articles.append(article)
        time.sleep(0.5)
    return all_articles


def fetch_market_data(tickers: dict) -> dict:
    """Yahoo Finance로 시장 지표 수집. 실패한 항목은 None."""
    if not tickers:
        return {}
    print("\n[시장 데이터] 수집 중...")
    market = {}
    for label, ticker in tickers.items():
        result = get_intraday_change(ticker)
        if result:
            market[label] = {
                "price": result["current_price"],
                "change_pct": result["change_pct"],
            }
            sign = "+" if result["change_pct"] >= 0 else ""
            print(f"  {label}: {result['current_price']} ({sign}{result['change_pct']}%)")
        else:
            market[label] = None
            print(f"  {label}: 수집 실패")
    return market


def run(newsletter_id: str) -> Path:
    config_path = DATA_DIR / f"newsletter_config_{newsletter_id}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"설정 파일 없음: {config_path}")

    config = json.loads(config_path.read_text(encoding="utf-8"))
    print(f"\n{'='*50}")
    print(f"[수집] 뉴스레터 {newsletter_id}: {config['name']}")
    print(f"{'='*50}")

    print("\n[RSS] 피드 수집 시작...")
    articles = fetch_all_rss(config["sources"])
    print(f"\n총 {len(articles)}개 기사 수집 완료")

    market_data = fetch_market_data(config.get("market_tickers", {}))

    output = {
        "newsletter_id": newsletter_id,
        "collected_at": datetime.now(KST).isoformat(),
        "date": datetime.now(KST).strftime("%Y-%m-%d"),
        "market_data": market_data,
        "articles": articles,
    }

    out_path = DATA_DIR / f"_temp_newsletter_{newsletter_id}.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[완료] {out_path}")
    return out_path


if __name__ == "__main__":
    nid = sys.argv[1].upper() if len(sys.argv) > 1 else "A"
    run(nid)
