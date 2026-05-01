"""
한국 종목명 → 티커 변환 유틸
FinanceDataReader로 KOSPI/KOSDAQ 전체 목록을 캐싱, 이름으로 티커 검색
"""
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

try:
    import FinanceDataReader as fdr
    FDR_AVAILABLE = True
except ImportError:
    FDR_AVAILABLE = False

CACHE_PATH = Path(__file__).parent.parent / "data" / "kr_stocks_cache.json"
CACHE_TTL_HOURS = 24


def _load_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_cache(data: dict):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _is_cache_fresh(cache: dict) -> bool:
    updated = cache.get("updated_at")
    if not updated:
        return False
    age = datetime.now() - datetime.fromisoformat(updated)
    return age < timedelta(hours=CACHE_TTL_HOURS)


def _fetch_listings() -> list:
    """KOSPI + KOSDAQ 전체 종목 목록 수집"""
    stocks = []
    for market in ["KOSPI", "KOSDAQ"]:
        suffix = ".KS" if market == "KOSPI" else ".KQ"
        try:
            df = fdr.StockListing(market)
            for _, row in df.iterrows():
                code = str(row.get("Code", row.get("Symbol", ""))).zfill(6)
                name = str(row.get("Name", "")).strip()
                if code and name:
                    stocks.append({"name": name, "ticker": f"{code}{suffix}", "market": market})
        except Exception as e:
            print(f"[KR Stocks] {market} 수집 실패: {e}")
    return stocks


def get_listings() -> list:
    """캐시된 종목 목록 반환 (만료 시 갱신)"""
    cache = _load_cache()
    if _is_cache_fresh(cache) and cache.get("stocks"):
        return cache["stocks"]

    if not FDR_AVAILABLE:
        return []

    print("[KR Stocks] 종목 목록 갱신 중...")
    stocks = _fetch_listings()
    _save_cache({"updated_at": datetime.now().isoformat(), "stocks": stocks})
    print(f"[KR Stocks] {len(stocks)}개 종목 캐시 완료")
    return stocks


def is_korean(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text))


def find_ticker(name: str) -> list[dict]:
    """
    종목명으로 티커 검색
    반환: [{"name": ..., "ticker": ..., "market": ...}, ...]
    완전 일치 우선, 없으면 부분 일치
    """
    stocks = get_listings()
    if not stocks:
        return []

    name = name.strip()

    # 완전 일치
    exact = [s for s in stocks if s["name"] == name]
    if exact:
        return exact

    # 부분 일치 (포함)
    partial = [s for s in stocks if name in s["name"] or s["name"] in name]
    return partial[:5]


def resolve_ticker(input_str: str) -> tuple[str | None, str | None]:
    """
    입력값을 티커로 변환
    반환: (ticker, name) 또는 (None, None) — 여러 후보면 None 반환
    """
    input_str = input_str.strip()

    # 이미 티커 형식인 경우 그대로 반환
    if re.match(r"^\d{6}\.(KS|KQ)$", input_str, re.IGNORECASE):
        return input_str.upper(), None
    if re.match(r"^[A-Za-z]{1,5}$", input_str):
        return input_str.upper(), None

    # 한국어 이름인 경우 검색
    if is_korean(input_str):
        results = find_ticker(input_str)
        if len(results) == 1:
            return results[0]["ticker"], results[0]["name"]
        return None, None  # 후보 여러 개 — 호출자가 처리

    return None, None


if __name__ == "__main__":
    tests = ["삼성전자", "SK하이닉스", "한화에어로스페이스", "카카오", "셀트리온"]
    for t in tests:
        results = find_ticker(t)
        print(f"{t}: {results}")
