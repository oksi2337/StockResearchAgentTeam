"""
newsletter_ai.py — 2단계 AI 체인으로 뉴스레터 초안 생성
Step 1: Haiku — 기사에서 핵심 사실 추출 + 섹션별 재료 선정
Step 2: Sonnet — 섹션별 완성 한국어 본문 생성
출력: research/newsletter_{A|B}_{YYYYMMDD}.md
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import anthropic
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT / ".env")

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = ROOT / "data"
RESEARCH_DIR = ROOT / "research"
RESEARCH_DIR.mkdir(exist_ok=True)

KST = timezone(timedelta(hours=9))
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"

# ─── Step 1: Haiku 사실 추출 ──────────────────────────────────────────────────

HAIKU_SYSTEM = """당신은 뉴스 팩트체커입니다.
입력된 뉴스 기사 목록을 분석해서 반드시 아래 JSON 형식으로만 응답하세요.
다른 설명 없이 순수 JSON만 출력하세요.

규칙:
- 각 기사에서 [날짜, 수치, 인명, 기관명, 핵심 사실]만 추출
- 추론, 의견, 예측 절대 금지 — 원문에 명시된 내용만
- 수치는 원문 그대로 (단위 포함)
- 기사당 facts 3개 이내

{
  "top_stories": [
    {"rank": 1, "source": "출처명", "url": "링크", "headline": "한 줄 핵심 (50자 이내)", "facts": ["사실1", "사실2"]},
    {"rank": 2, ...},
    {"rank": 3, ...}
  ],
  "deep_dive": {
    "source": "출처명", "url": "링크", "topic": "딥다이브 주제",
    "why_important": ["왜 중요한 사실1", "사실2"],
    "korea_impact": ["한국 영향 사실1", "사실2"],
    "outlook": ["향후 전망 사실1", "사실2"]
  },
  "short_items": [
    {"source": "출처명", "url": "링크", "headline": "한 줄 (40자 이내)"},
    ...
  ],
  "reading_list": [
    {"source": "출처명", "url": "링크", "title": "제목", "one_line": "한 줄 소개"}
  ]
}"""


def step1_extract_facts(articles: list[dict], newsletter_id: str) -> dict:
    """Haiku로 기사에서 사실 추출 및 섹션별 재료 선정."""
    articles_text = "\n\n".join(
        f"[{i+1}] 출처: {a['source']}\n제목: {a['title']}\n요약: {a['summary']}\n링크: {a['url']}"
        for i, a in enumerate(articles[:50])
    )

    if newsletter_id == "A":
        task = "글로벌 정치·경제 뉴스레터용. top_stories는 글로벌 정치·경제 빅뉴스 3개, deep_dive는 한국 독자에게 가장 중요한 이슈, short_items는 흥미로운 단신 5개."
    else:
        task = "AI 트렌드 뉴스레터용. top_stories는 주요 AI 기업 발표 3개, deep_dive는 AI 활용 케이스 스터디, short_items는 새로운 AI 도구 3개 + 한국 AI 동향 2개, reading_list는 추천 아티클 5개."

    print(f"[Step 1] Haiku 사실 추출 시작... ({len(articles[:50])}개 기사)")
    response = client.messages.create(
        model=HAIKU,
        max_tokens=4096,
        system=HAIKU_SYSTEM,
        messages=[{
            "role": "user",
            "content": f"작업: {task}\n\n아래 기사 목록을 분석하세요:\n\n{articles_text}"
        }]
    )

    full_text = response.content[0].text
    try:
        start = full_text.find("{")
        end = full_text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(full_text[start:end])
    except Exception as e:
        print(f"[Step 1] JSON 파싱 실패: {e}\n원본:\n{full_text[:300]}")
    return {}


# ─── Step 2: Sonnet 본문 생성 ─────────────────────────────────────────────────

def _make_sonnet_prompt_A(facts: dict, date_str: str, tone: str) -> str:
    return f"""당신은 한국 경제·시사 뉴스레터 에디터입니다.
오늘 날짜: {date_str}

아래 사실(facts) 자료를 바탕으로 뉴스레터 A '글로벌 정치·경제 브리핑' 초안을 작성하세요.

톤 가이드: {tone}

수치 규칙 (매우 중요):
- 시장 브리핑 수치(환율/지수/유가)는 [MARKET_DATA] 자리표시자를 그대로 사용. 절대 수치 생성 금지.
- 나머지 수치는 반드시 아래 facts에서만 인용. 없으면 수치 생략.

확인 필요 항목 표시:
- 검증이 필요한 수치나 고유명사 앞에 ⚠️ 붙이기

출력 형식 (마크다운, 섹션 순서 고정):

## 📢 오늘의 헤드라인 3
1. [헤드라인] — [출처] ([링크])
2. [헤드라인] — [출처] ([링크])
3. [헤드라인] — [출처] ([링크])

## 📊 시장 브리핑
[MARKET_DATA]

## 🔍 딥다이브: [주제]
**왜 중요한가**
[1문단]

**한국 영향**
[1문단]

**향후 전망**
[1문단]

**한 줄 결론**
[1문장]

_출처: [출처명] — [링크]_

## 📋 이런 뉴스도 있었어요
- [단신1] — [출처] ([링크])
- [단신2] — [출처] ([링크])
- [단신3] — [출처] ([링크])
- [단신4] — [출처] ([링크])
- [단신5] — [출처] ([링크])

## 💡 오늘의 한 줄 인사이트
> [오늘 뉴스를 관통하는 핵심 인사이트 1문장]

---

아래는 Step 1에서 추출한 facts 자료입니다:

{json.dumps(facts, ensure_ascii=False, indent=2)}"""


def _make_sonnet_prompt_B(facts: dict, date_str: str, tone: str) -> str:
    return f"""당신은 AI 트렌드 뉴스레터 에디터입니다.
오늘 날짜: {date_str}

아래 사실(facts) 자료를 바탕으로 뉴스레터 B 'AI 트렌드 브리핑' 초안을 작성하세요.

톤 가이드: {tone}

수치 규칙: 반드시 아래 facts에서만 인용. 없으면 수치 생략. 절대 수치 생성 금지.

확인 필요 항목 표시:
- 검증이 필요한 수치나 고유명사 앞에 ⚠️ 붙이기

출력 형식 (마크다운, 섹션 순서 고정):

## 🚀 이번 주 빅뉴스
[OpenAI·Anthropic·구글·메타 등 주요 발표 2~3개, 각 1~2문단]

_출처: [출처명] — [링크]_

## 🛠️ 새로 나온 도구 3
1. **[도구명]** — [한 줄 설명] / 써볼 이유: [한 줄 평가] ([링크])
2. **[도구명]** — [한 줄 설명] / 써볼 이유: [한 줄 평가] ([링크])
3. **[도구명]** — [한 줄 설명] / 써볼 이유: [한 줄 평가] ([링크])

## 📖 케이스 스터디: [주제]
[국내외 AI 실제 활용 사례 심층 분석, 3~4문단]

_출처: [출처명] — [링크]_

## 🇰🇷 한국 AI 동향
- [네이버·카카오·국내 스타트업 소식1] — [출처] ([링크])
- [소식2] — [출처] ([링크])

## 📚 이번 주 읽을거리
1. [제목] — [한 줄 소개] ([링크])
2. [제목] — [한 줄 소개] ([링크])
3. [제목] — [한 줄 소개] ([링크])
4. [제목] — [한 줄 소개] ([링크])
5. [제목] — [한 줄 소개] ([링크])

---

아래는 Step 1에서 추출한 facts 자료입니다:

{json.dumps(facts, ensure_ascii=False, indent=2)}"""


def step2_generate_draft(facts: dict, config: dict, date_str: str) -> str:
    """Sonnet으로 뉴스레터 본문 생성."""
    newsletter_id = config["id"]
    tone = config.get("tone_guide", "")

    if newsletter_id == "A":
        prompt = _make_sonnet_prompt_A(facts, date_str, tone)
    else:
        prompt = _make_sonnet_prompt_B(facts, date_str, tone)

    print(f"[Step 2] Sonnet 본문 생성 중...")
    response = client.messages.create(
        model=SONNET,
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text


def inject_market_data(draft: str, market_data: dict) -> str:
    """[MARKET_DATA] placeholder에 Yahoo Finance 수집 데이터 주입."""
    if not market_data:
        return draft.replace("[MARKET_DATA]", "_시장 데이터 수집 실패 — 수동 입력 필요_")

    lines = []
    for label, data in market_data.items():
        if data is None:
            lines.append(f"| {label} | — | 수집 실패 |")
        else:
            price = data["price"]
            pct = data["change_pct"]
            sign = "+" if pct >= 0 else ""
            arrow = "▲" if pct >= 0 else "▼"
            lines.append(f"| {label} | {price:,} | {arrow} {sign}{pct}% |")

    table = "| 지표 | 현재가 | 전일 대비 |\n|------|--------|----------|\n" + "\n".join(lines)
    return draft.replace("[MARKET_DATA]", table)


def add_header(draft: str, config: dict, date_str: str) -> str:
    """초안 상단에 메타 헤더 추가."""
    header = (
        f"# {config['name']} — {date_str}\n\n"
        f"> **검수 상태**: ⏳ 검수 전 | "
        f"**생성 시각**: {datetime.now(KST).strftime('%H:%M')} KST\n\n"
        f"⚠️ 표시 항목은 수치·고유명사 확인 필요\n\n---\n\n"
    )
    return header + draft


def run(newsletter_id: str) -> Path:
    temp_path = DATA_DIR / f"_temp_newsletter_{newsletter_id}.json"
    if not temp_path.exists():
        raise FileNotFoundError(f"수집 파일 없음: {temp_path} (newsletter_collect.py 먼저 실행)")

    raw = json.loads(temp_path.read_text(encoding="utf-8"))
    config_path = DATA_DIR / f"newsletter_config_{newsletter_id}.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    articles = raw["articles"]
    market_data = raw.get("market_data", {})
    date_str = raw["date"]

    print(f"\n{'='*50}")
    print(f"[AI] 뉴스레터 {newsletter_id} 초안 생성")
    print(f"{'='*50}")

    facts = step1_extract_facts(articles, newsletter_id)
    if not facts:
        print("[경고] Step 1 실패 — 빈 facts로 Step 2 진행")

    draft = step2_generate_draft(facts, config, date_str)
    draft = inject_market_data(draft, market_data)
    draft = add_header(draft, config, date_str)

    date_compact = date_str.replace("-", "")
    out_path = RESEARCH_DIR / f"newsletter_{newsletter_id}_{date_compact}.md"
    out_path.write_text(draft, encoding="utf-8")
    print(f"\n[완료] {out_path}")
    return out_path


if __name__ == "__main__":
    nid = sys.argv[1].upper() if len(sys.argv) > 1 else "A"
    run(nid)
