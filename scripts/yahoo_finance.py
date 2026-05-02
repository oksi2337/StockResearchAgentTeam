import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


def get_price_data(ticker: str, period: str = "3mo") -> Optional[pd.DataFrame]:
    """OHLCV 데이터 수집"""
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"[야후파이낸스] {ticker} 가격 수집 실패: {e}")
        return None


def get_technical_indicators(ticker: str) -> Optional[dict]:
    """기술적 지표 계산"""
    df = get_price_data(ticker, period="1y")
    if df is None or len(df) < 20:
        return None

    close = df["Close"]
    current_price = float(close.iloc[-1])
    prev_close = float(close.iloc[-2])

    # 이동평균
    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

    # RSI (14일)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = float(100 - (100 / (1 + rs)).iloc[-1])

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = float((ema12 - ema26).iloc[-1])
    signal_line = float((ema12 - ema26).ewm(span=9).mean().iloc[-1])

    # 52주 고저
    week52_high = float(close.rolling(252).max().iloc[-1]) if len(close) >= 252 else float(close.max())
    week52_low = float(close.rolling(252).min().iloc[-1]) if len(close) >= 252 else float(close.min())

    # 거래량
    avg_volume = float(df["Volume"].rolling(20).mean().iloc[-1])
    current_volume = float(df["Volume"].iloc[-1])

    # 전일 대비 변화율
    change_pct = (current_price - prev_close) / prev_close * 100

    return {
        "ticker": ticker,
        "current_price": round(current_price, 2),
        "change_pct": round(change_pct, 2),
        "ma20": round(ma20, 2),
        "ma50": round(ma50, 2) if ma50 else None,
        "ma200": round(ma200, 2) if ma200 else None,
        "rsi": round(rsi, 1),
        "macd": round(macd_line, 4),
        "macd_signal": round(signal_line, 4),
        "macd_hist": round(macd_line - signal_line, 4),
        "week52_high": round(week52_high, 2),
        "week52_low": round(week52_low, 2),
        "price_vs_52h": round((current_price - week52_high) / week52_high * 100, 1),
        "price_vs_52l": round((current_price - week52_low) / week52_low * 100, 1),
        "volume": int(current_volume),
        "avg_volume_20d": int(avg_volume),
        "volume_ratio": round(current_volume / avg_volume, 2) if avg_volume else None,
        "collected_at": datetime.now().isoformat(),
    }


def get_fundamentals(ticker: str) -> Optional[dict]:
    """펀더멘탈 데이터 수집"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "ticker": ticker,
            "name": info.get("longName", ticker),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "dividend_yield": info.get("dividendYield"),
            "eps": info.get("trailingEps"),
            "revenue": info.get("totalRevenue"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "profit_margin": info.get("profitMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "roe": info.get("returnOnEquity"),
            "analyst_target": info.get("targetMeanPrice"),
            "recommendation": info.get("recommendationKey", ""),
            "collected_at": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"[야후파이낸스] {ticker} 펀더멘탈 수집 실패: {e}")
        return None


def get_intraday_change(ticker: str) -> Optional[dict]:
    """현재가 vs 전일 종가 변화율 (실시간 polling용)"""
    try:
        fi = yf.Ticker(ticker).fast_info
        current = getattr(fi, "last_price", None)
        prev_close = getattr(fi, "previous_close", None)
        if current and prev_close and prev_close > 0:
            change_pct = (current - prev_close) / prev_close * 100
            return {"ticker": ticker, "current_price": round(current, 2), "change_pct": round(change_pct, 2)}
    except Exception:
        pass

    # fast_info 실패 시 일별 데이터로 폴백
    df = get_price_data(ticker, period="5d")
    if df is None or len(df) < 2:
        return None
    close = df["Close"]
    current = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    if prev <= 0:
        return None
    return {"ticker": ticker, "current_price": round(current, 2), "change_pct": round((current - prev) / prev * 100, 2)}


def check_alerts(ticker: str, threshold_pct: float = 5.0) -> Optional[dict]:
    """가격 급변 감지"""
    df = get_price_data(ticker, period="5d")
    if df is None or len(df) < 2:
        return None

    close = df["Close"]
    change_pct = (float(close.iloc[-1]) - float(close.iloc[-2])) / float(close.iloc[-2]) * 100

    if abs(change_pct) >= threshold_pct:
        return {
            "ticker": ticker,
            "change_pct": round(change_pct, 2),
            "current_price": round(float(close.iloc[-1]), 2),
            "alert": "급등" if change_pct > 0 else "급락",
        }
    return None


if __name__ == "__main__":
    result = get_technical_indicators("AAPL")
    print(result)
