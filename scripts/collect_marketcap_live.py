"""
collect_marketcap_live.py — yfinance로 글로벌 시총 상위 종목 실시간 수집
run_daily.py에서 collect_and_save()를 호출해 사용 (NAS 독립 실행 지원)
"""
from __future__ import annotations
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yfinance as yf

DATA_DIR = Path(__file__).parent.parent / "data"
KST = timezone(timedelta(hours=9))

# 글로벌 시총 상위 ~110개 유니버스: (ticker, name, sector, country)
UNIVERSE = [
    # --- Technology ---
    ("NVDA", "Nvidia", "Technology", "US"),
    ("AAPL", "Apple", "Technology", "US"),
    ("MSFT", "Microsoft", "Technology", "US"),
    ("GOOGL", "Alphabet", "Technology", "US"),
    ("META", "Meta Platforms", "Technology", "US"),
    ("AVGO", "Broadcom", "Technology", "US"),
    ("ORCL", "Oracle", "Technology", "US"),
    ("ADBE", "Adobe", "Technology", "US"),
    ("AMD", "AMD", "Technology", "US"),
    ("QCOM", "Qualcomm", "Technology", "US"),
    ("TXN", "Texas Instruments", "Technology", "US"),
    ("AMAT", "Applied Materials", "Technology", "US"),
    ("MU", "Micron Technology", "Technology", "US"),
    ("INTC", "Intel", "Technology", "US"),
    ("NOW", "ServiceNow", "Technology", "US"),
    ("INTU", "Intuit", "Technology", "US"),
    ("CRM", "Salesforce", "Technology", "US"),
    ("CSCO", "Cisco", "Technology", "US"),
    ("ACN", "Accenture", "Technology", "US"),
    ("IBM", "IBM", "Technology", "US"),
    ("UBER", "Uber", "Technology", "US"),
    ("PLTR", "Palantir", "Technology", "US"),
    ("NFLX", "Netflix", "Technology", "US"),
    ("T", "AT&T", "Technology", "US"),
    ("VZ", "Verizon", "Technology", "US"),
    ("CMCSA", "Comcast", "Technology", "US"),
    ("TSM", "TSMC", "Technology", "TW"),
    ("ASML", "ASML", "Technology", "NL"),
    ("SAP", "SAP", "Technology", "DE"),
    ("005930.KS", "Samsung Electronics", "Technology", "KR"),
    ("0700.HK", "Tencent", "Technology", "CN"),
    # --- Consumer ---
    ("AMZN", "Amazon", "Consumer", "US"),
    ("TSLA", "Tesla", "Consumer", "US"),
    ("WMT", "Walmart", "Consumer", "US"),
    ("COST", "Costco", "Consumer", "US"),
    ("HD", "Home Depot", "Consumer", "US"),
    ("MCD", "McDonald's", "Consumer", "US"),
    ("SBUX", "Starbucks", "Consumer", "US"),
    ("NKE", "Nike", "Consumer", "US"),
    ("PG", "Procter & Gamble", "Consumer", "US"),
    ("KO", "Coca-Cola", "Consumer", "US"),
    ("PEP", "PepsiCo", "Consumer", "US"),
    ("PM", "Philip Morris", "Consumer", "US"),
    ("BKNG", "Booking Holdings", "Consumer", "US"),
    ("DIS", "Disney", "Consumer", "US"),
    ("BABA", "Alibaba", "Consumer", "CN"),
    ("PDD", "PDD Holdings", "Consumer", "CN"),
    ("TM", "Toyota", "Consumer", "JP"),
    ("MC.PA", "LVMH", "Consumer", "FR"),
    ("RMS.PA", "Hermès", "Consumer", "FR"),
    # --- Finance ---
    ("BRK-B", "Berkshire Hathaway", "Finance", "US"),
    ("JPM", "JPMorgan Chase", "Finance", "US"),
    ("V", "Visa", "Finance", "US"),
    ("MA", "Mastercard", "Finance", "US"),
    ("BAC", "Bank of America", "Finance", "US"),
    ("GS", "Goldman Sachs", "Finance", "US"),
    ("MS", "Morgan Stanley", "Finance", "US"),
    ("WFC", "Wells Fargo", "Finance", "US"),
    ("SPGI", "S&P Global", "Finance", "US"),
    ("BLK", "BlackRock", "Finance", "US"),
    ("AXP", "American Express", "Finance", "US"),
    ("HSBC", "HSBC", "Finance", "UK"),
    ("RY", "Royal Bank of Canada", "Finance", "CA"),
    ("TD", "TD Bank", "Finance", "CA"),
    ("CBA.AX", "Commonwealth Bank", "Finance", "AU"),
    # --- Healthcare ---
    ("LLY", "Eli Lilly", "Healthcare", "US"),
    ("UNH", "UnitedHealth", "Healthcare", "US"),
    ("JNJ", "Johnson & Johnson", "Healthcare", "US"),
    ("ABBV", "AbbVie", "Healthcare", "US"),
    ("MRK", "Merck", "Healthcare", "US"),
    ("PFE", "Pfizer", "Healthcare", "US"),
    ("TMO", "Thermo Fisher", "Healthcare", "US"),
    ("AMGN", "Amgen", "Healthcare", "US"),
    ("ABT", "Abbott Laboratories", "Healthcare", "US"),
    ("DHR", "Danaher", "Healthcare", "US"),
    ("ISRG", "Intuitive Surgical", "Healthcare", "US"),
    ("REGN", "Regeneron", "Healthcare", "US"),
    ("VRTX", "Vertex Pharmaceuticals", "Healthcare", "US"),
    ("GILD", "Gilead Sciences", "Healthcare", "US"),
    ("SYK", "Stryker", "Healthcare", "US"),
    ("BSX", "Boston Scientific", "Healthcare", "US"),
    ("BMY", "Bristol-Myers Squibb", "Healthcare", "US"),
    ("MDT", "Medtronic", "Healthcare", "US"),
    ("NVO", "Novo Nordisk", "Healthcare", "DK"),
    ("AZN", "AstraZeneca", "Healthcare", "UK"),
    ("NVS", "Novartis", "Healthcare", "CH"),
    ("RHHBY", "Roche", "Healthcare", "CH"),
    ("GSK", "GSK", "Healthcare", "UK"),
    ("SNY", "Sanofi", "Healthcare", "FR"),
    # --- Energy ---
    ("XOM", "Exxon Mobil", "Energy", "US"),
    ("CVX", "Chevron", "Energy", "US"),
    ("COP", "ConocoPhillips", "Energy", "US"),
    ("SHEL", "Shell", "Energy", "UK"),
    ("TTE", "TotalEnergies", "Energy", "FR"),
    ("2222.SR", "Saudi Aramco", "Energy", "SA"),
    ("RELIANCE.NS", "Reliance Industries", "Energy", "IN"),
    # --- Industrial ---
    ("GE", "GE Aerospace", "Industrial", "US"),
    ("CAT", "Caterpillar", "Industrial", "US"),
    ("HON", "Honeywell", "Industrial", "US"),
    ("RTX", "RTX", "Industrial", "US"),
    ("BA", "Boeing", "Industrial", "US"),
    ("UPS", "UPS", "Industrial", "US"),
    ("DE", "Deere & Company", "Industrial", "US"),
    ("LMT", "Lockheed Martin", "Industrial", "US"),
    ("UNP", "Union Pacific", "Industrial", "US"),
    ("LIN", "Linde", "Industrial", "US"),
    ("BHP", "BHP Group", "Industrial", "AU"),
    ("SIE.DE", "Siemens", "Industrial", "DE"),
]

# 로컬 통화 환산이 필요한 티커 (yfinance가 로컬 통화로 market_cap 반환)
TICKER_CURRENCY: dict[str, str] = {
    "005930.KS": "KRW",
    "0700.HK":   "HKD",
    "2222.SR":   "SAR",
    "MC.PA":     "EUR",
    "RMS.PA":    "EUR",
    "SIE.DE":    "EUR",
    "CBA.AX":    "AUD",
    "RELIANCE.NS": "INR",
}

EXCHANGE_BY_SUFFIX = {
    ".KS": "KRX", ".KQ": "KOSDAQ",
    ".HK": "HKEX", ".SR": "TADAWUL",
    ".PA": "Euronext", ".DE": "XETRA",
    ".AX": "ASX", ".NS": "NSE",
}

NASDAQ_TICKERS = {
    "NVDA","AAPL","MSFT","GOOGL","META","AMZN","AVGO","ORCL","ADBE",
    "AMD","QCOM","TXN","AMAT","MU","INTC","NOW","INTU","CRM","CSCO",
    "PLTR","NFLX","CMCSA","TSM","ASML","COST","SBUX","ISRG","REGN",
    "VRTX","GILD","NVO","AZN","NVS","RHHBY","SNY","GSK","BKNG","PDD","BIDU",
}


def _get_exchange(ticker: str) -> str:
    for suffix, ex in EXCHANGE_BY_SUFFIX.items():
        if ticker.endswith(suffix):
            return ex
    return "NASDAQ" if ticker in NASDAQ_TICKERS else "NYSE"


def fetch_fx_rates() -> dict[str, float]:
    """각 통화의 USD 환산 계수 반환: {currency: usd_per_1_unit}"""
    # KRW=X → 1 USD = X KRW  → 1 KRW = 1/X USD (is_inverse=True)
    # EURUSD=X → 1 EUR = X USD → 1 EUR = X USD (is_inverse=False)
    specs = {
        "KRW": ("KRW=X",    True),
        "HKD": ("HKD=X",    True),
        "SAR": ("SAR=X",    True),
        "INR": ("INR=X",    True),
        "EUR": ("EURUSD=X", False),
        "AUD": ("AUDUSD=X", False),
    }
    rates: dict[str, float] = {}
    for currency, (pair, is_inverse) in specs.items():
        try:
            val = yf.Ticker(pair).fast_info.last_price
            if val and val > 0:
                rates[currency] = (1.0 / val) if is_inverse else val
        except Exception as e:
            print(f"[FX] {pair} 실패: {e}")
    return rates


def _fetch_one(entry: tuple, fx_rates: dict[str, float]) -> dict | None:
    ticker, name, sector, country = entry
    try:
        fi = yf.Ticker(ticker).fast_info

        mc_local: float | None = getattr(fi, "market_cap", None)
        if not mc_local or mc_local <= 0:
            return None

        last_price: float = getattr(fi, "last_price", None) or 0
        prev_close: float = getattr(fi, "previous_close", None) or 0

        # 등락률은 로컬 통화 기준이므로 환율 무관
        change_pct = 0.0
        if last_price > 0 and prev_close > 0:
            change_pct = (last_price - prev_close) / prev_close * 100

        # USD 환산
        currency = TICKER_CURRENCY.get(ticker, "USD")
        usd_rate = fx_rates.get(currency, 1.0) if currency != "USD" else 1.0

        return {
            "ticker":        ticker,
            "name":          name,
            "exchange":      _get_exchange(ticker),
            "country":       country,
            "sector":        sector,
            "market_cap_usd": round(mc_local * usd_rate),
            "price_usd":     round(last_price * usd_rate, 4),
            "change_1d_pct": round(change_pct, 2),
        }
    except Exception as e:
        print(f"[{ticker}] 수집 실패: {e}")
        return None


def collect_and_save() -> dict | None:
    """시총 데이터 수집 → data/marketcap-YYYY-MM-DD.json 저장. 실패 시 None 반환."""
    today = datetime.now(KST).strftime("%Y-%m-%d")
    print(f"[시총 수집] 시작: {today}, {len(UNIVERSE)}개 종목")

    # 1. FX 환율
    fx_rates = fetch_fx_rates()
    krw_usd_rate = 1.0 / fx_rates.get("KRW", 1 / 1350)  # 1 USD = X KRW
    print(f"[시총 수집] USD/KRW: {krw_usd_rate:.0f}, 수집된 환율: {list(fx_rates.keys())}")

    # 2. 병렬 수집
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(_fetch_one, e, fx_rates): e[0] for e in UNIVERSE}
        for future in as_completed(futures):
            r = future.result()
            if r:
                results.append(r)

    if not results:
        print("[시총 수집] 수집된 데이터 없음 — 저장 스킵")
        return None

    # 3. 정렬 및 순위 부여
    results.sort(key=lambda x: x["market_cap_usd"], reverse=True)
    for i, entry in enumerate(results, 1):
        entry["rank"] = i
        entry["market_cap_krw"] = round(entry["market_cap_usd"] * krw_usd_rate)

    # 4. 저장
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {"date": today, "rate": round(krw_usd_rate), "data": results}

    out_path = DATA_DIR / f"marketcap-{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # index.json 업데이트
    index_path = DATA_DIR / "index.json"
    index: dict = {"dates": [], "lastCollected": "", "lastRate": 0}
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    dates: list = index.setdefault("dates", [])
    if today not in dates:
        dates.append(today)
        dates.sort()
    index["lastCollected"] = datetime.now(KST).isoformat()
    index["lastRate"] = round(krw_usd_rate)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[시총 수집] 완료: {len(results)}개 종목 → {out_path.name}")
    return data


if __name__ == "__main__":
    collect_and_save()
