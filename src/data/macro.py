"""Fetch global macro data via yfinance."""
import yfinance as yf


def fetch_macro_data() -> dict:
    tickers = {
        "usdtry": "USDTRY=X",
        "oil_brent": "BZ=F",
        "vix": "^VIX",
        "sp500": "^GSPC",
        "gold": "GC=F",
    }
    result = {}
    for key, symbol in tickers.items():
        try:
            data = yf.Ticker(symbol).history(period="2d")["Close"]
            result[key] = round(float(data.iloc[-1]), 2)
            result[f"{key}_change_pct"] = round(
                float((data.iloc[-1] - data.iloc[-2]) / data.iloc[-2] * 100), 2
            )
        except Exception:
            result[key] = None
            result[f"{key}_change_pct"] = None
    return result
