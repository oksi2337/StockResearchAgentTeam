"""
리서치 에이전트가 만든 md 파일을 파싱하여 딕셔너리로 변환.

입력: research/[티커]_[YYYYMMDD].md
출력: dict with keys (ticker, company, date, fields, analyst_ratings)
"""
import re
import sys
from pathlib import Path


# 표에서 추출할 항목명 (md에 나오는 정확한 라벨)
TABLE_FIELDS = [
    "기업 개요",
    "주간 성과",
    "주간 주가 변동 주된 사유",
    "주가의 위치 (단기)",
    "주가의 위치 (중장기)",
    "기업 경쟁력",
    "포워드 밸류에이션 추정",
    "최근 일주일간 기업펀더멘털 변화",
    "향후 전망",
]

# placeholder 패턴 (사용자 직접 입력 필요)
PLACEHOLDER_PATTERN = re.compile(r"✏️\s*\*\*직접\s*입력\*\*")


def parse_md(md_path: str | Path) -> dict:
    """md 파일을 읽어서 구조화된 딕셔너리로 반환."""
    md_path = Path(md_path)
    text = md_path.read_text(encoding="utf-8")

    result = {
        "source_file": str(md_path),
        "ticker": "",
        "company": "",
        "date": "",
        "fields": {},
        "analyst_ratings": [],
        "news_items": [],
        "missing_fields": [],
    }

    # 1. 제목에서 회사명/티커 추출
    # 예: "# 학습 기업 | TSMC TSM" 또는 "# 학습 기업 | TSMC (TSM)"
    title_match = re.search(r"^#\s*학습\s*기업\s*\|\s*(.+)$", text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        # 괄호 안 티커: "TSMC (TSM)"
        paren_match = re.match(r"^(.+?)\s*\(([^)]+)\)$", title)
        if paren_match:
            result["company"] = paren_match.group(1).strip()
            result["ticker"] = paren_match.group(2).strip()
        else:
            # 공백 구분: "TSMC TSM" — 마지막 토큰을 티커로
            parts = title.rsplit(maxsplit=1)
            if len(parts) == 2:
                result["company"] = parts[0].strip()
                result["ticker"] = parts[1].strip()
            else:
                result["company"] = title
                result["ticker"] = title

    # 2. 작성일 추출
    # 예: "> 작성일: 2026-04-26"
    date_match = re.search(r">\s*작성일\s*[::]\s*(.+)$", text, re.MULTILINE)
    if date_match:
        result["date"] = date_match.group(1).strip()

    # 파일명에서 날짜 보충 (위에서 못 찾았을 때)
    if not result["date"]:
        fname_match = re.search(r"(\d{8}|\d{4}-\d{2}-\d{2})", md_path.stem)
        if fname_match:
            raw = fname_match.group(1)
            if len(raw) == 8:  # YYYYMMDD → YYYY-MM-DD
                result["date"] = f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"
            else:
                result["date"] = raw

    # 3. 표 안의 항목 추출
    # 패턴: | 항목명 | 내용 |
    for field in TABLE_FIELDS:
        # 정규식 특수문자 이스케이프
        escaped = re.escape(field)
        pattern = rf"\|\s*{escaped}\s*\|\s*(.+?)\s*\|"
        m = re.search(pattern, text)
        if m:
            value = m.group(1).strip()
            # placeholder 감지
            if PLACEHOLDER_PATTERN.search(value) or "확인 필요" in value:
                result["fields"][field] = ""
                result["missing_fields"].append(field)
            else:
                result["fields"][field] = value
        else:
            result["fields"][field] = ""
            result["missing_fields"].append(field)

    # 4. 증권사 평가 섹션 추출
    # "### 주간 증권사 평가" 다음 줄부터 다음 헤더(또는 EOF)까지
    rating_section = re.search(
        r"###\s*주간\s*증권사\s*평가\s*\n(.*?)(?=\n#{1,3}\s|\Z)",
        text,
        re.DOTALL,
    )
    if rating_section:
        for line in rating_section.group(1).splitlines():
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                # 불릿 기호 제거
                rating = re.sub(r"^[-*]\s*", "", line).strip()
                if rating:
                    result["analyst_ratings"].append(rating)

    # 5. 주요 뉴스 섹션 추출
    # "### 주요 뉴스" 다음 줄부터 다음 헤더(또는 EOF)까지
    # 형식: - **뉴스 제목**: 내용 요약
    news_section = re.search(
        r"###\s*주요\s*뉴스\s*\n(.*?)(?=\n#{1,3}\s|\Z)",
        text,
        re.DOTALL,
    )
    if news_section:
        for line in news_section.group(1).splitlines():
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                line = re.sub(r"^[-*]\s*", "", line).strip()
                m = re.match(r"\*\*(.+?)\*\*[:\s]+(.+)", line)
                if m:
                    result["news_items"].append({
                        "title": m.group(1).strip(),
                        "summary": m.group(2).strip(),
                    })
                elif line:
                    result["news_items"].append({"title": line, "summary": ""})

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_md.py <md_file_path>")
        sys.exit(1)

    parsed = parse_md(sys.argv[1])
    import json
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
