"""
Core market data functionality - yfinance business logic
Testable independently of MCP protocol layer
"""

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import yfinance as yf  # type: ignore[import-untyped]

# Constants
WEEKEND_START_DAY = 5  # Saturday (Monday = 0, Sunday = 6)

# Category to symbol mappings (for get_market_snapshot)
CATEGORY_MAPPING: dict[str, list[str]] = {
    "us": ["sp500", "nasdaq", "dow"],
    "futures": ["es_futures", "nq_futures", "ym_futures"],
    "factors": ["gold", "btc", "vix", "oil_wti", "natgas", "us10y"],
    "europe": ["stoxx50", "dax", "ftse"],
    "asia": ["nikkei", "hangseng", "shanghai"],
    "crypto": ["btc", "eth"],
    "commodities": ["gold", "oil_wti", "natgas"],
    "bonds": ["us10y", "us2y", "us30y"],
    "all": [
        "es_futures", "nq_futures", "ym_futures",
        "gold", "btc", "vix",
        "oil_wti", "natgas",
        "us10y",
        "sp500", "nasdaq", "dow",
        "stoxx50", "dax", "ftse",
        "nikkei", "hangseng", "shanghai",
    ],
}

# Market snapshot symbol mappings
MARKET_SYMBOLS = {
    # US Indices
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "dow": "^DJI",
    "russell2000": "^RUT",

    # Futures
    "es_futures": "ES=F",      # S&P 500 futures
    "nq_futures": "NQ=F",      # Nasdaq futures
    "ym_futures": "YM=F",      # Dow futures
    "rty_futures": "RTY=F",    # Russell 2000 futures

    # European Indices
    "stoxx50": "^STOXX50E",
    "dax": "^GDAXI",
    "ftse": "^FTSE",
    "cac40": "^FCHI",

    # Asian Indices
    "nikkei": "^N225",
    "hangseng": "^HSI",
    "shanghai": "000001.SS",

    # Crypto (via futures)
    "btc": "BTC-USD",
    "eth": "ETH-USD",

    # Commodities
    "gold": "GC=F",
    "silver": "SI=F",
    "oil_wti": "CL=F",
    "oil_brent": "BZ=F",
    "natgas": "NG=F",

    # Bonds
    "us10y": "^TNX",
    "us2y": "^IRX",
    "us30y": "^TYX",

    # Volatility
    "vix": "^VIX",
}

# Formatting sections (for format_market_snapshot)
FORMATTING_SECTIONS: dict[str, list[str]] = {
    "BROAD MARKET FACTOR": ["es_futures", "nq_futures", "ym_futures"],
    "RISK FACTORS": ["gold", "btc", "vix"],
    "COMMODITY FACTORS": ["oil_wti", "natgas"],
    "RATE FACTOR": ["us10y"],
    "US INDICES": ["sp500", "nasdaq", "dow"],
    "EUROPE": ["stoxx50", "dax", "ftse"],
    "ASIA": ["nikkei", "hangseng", "shanghai"],
}

# Friendly display names
DISPLAY_NAMES: dict[str, str] = {
    "es_futures": "S&P 500", "nq_futures": "Nasdaq", "ym_futures": "Dow",
    "gold": "Gold", "btc": "Bitcoin", "vix": "VIX",
    "oil_wti": "Oil WTI", "natgas": "Nat Gas",
    "us10y": "US 10Y",
    "sp500": "S&P 500", "nasdaq": "Nasdaq", "dow": "Dow",
    "stoxx50": "STOXX 50", "dax": "DAX", "ftse": "FTSE",
    "nikkei": "Nikkei", "hangseng": "Hang Seng", "shanghai": "Shanghai",
}

# Factor annotations
FACTOR_ANNOTATIONS: dict[str, str] = {
    "gold": "Safe haven",
    "btc": "Risk-on",
    "vix": "Fear gauge",
    "us10y": "Fed policy",
}


def is_market_open() -> bool:
    """Check if US market is currently open (9:30 AM - 4:00 PM ET, Mon-Fri)"""
    now_et = datetime.now(ZoneInfo("America/New_York"))

    # Check if weekend
    if now_et.weekday() >= WEEKEND_START_DAY:
        return False

    # Check if within market hours (9:30 AM - 4:00 PM ET)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now_et < market_close


def get_ticker_data(symbol: str) -> dict[str, Any]:
    """Fetch current data for a single ticker"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        change_pct = info.get("regularMarketChangePercent")

        return {
            "symbol": symbol,
            "price": price,
            "change_percent": change_pct,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def get_market_snapshot(categories: list[str]) -> dict[str, dict[str, Any]]:
    """Get snapshot of multiple market categories"""
    # Performance: Use dict for O(1) category lookup instead of if/elif chain
    category_mapping: dict[str, list[str]] = {
        "us": ["sp500", "nasdaq", "dow"],
        "futures": ["es_futures", "nq_futures", "ym_futures"],
        "factors": ["gold", "btc", "vix", "oil_wti", "natgas", "us10y"],
        "europe": ["stoxx50", "dax", "ftse"],
        "asia": ["nikkei", "hangseng", "shanghai"],
        "crypto": ["btc", "eth"],
        "commodities": ["gold", "oil_wti", "natgas"],
        "bonds": ["us10y", "us2y", "us30y"],
        "all": ["es_futures", "nq_futures", "ym_futures",
                "gold", "btc", "vix",
                "oil_wti", "natgas",
                "us10y",
                "sp500", "nasdaq", "dow",
                "stoxx50", "dax", "ftse",
                "nikkei", "hangseng", "shanghai"],
    }

    # Auto-detect: if no categories specified, show smart default (factor view)
    if not categories:
        categories = ["us", "factors"] if is_market_open() else ["futures", "factors"]

    # Build symbol list based on categories
    symbols_to_fetch: list[str] = []
    for cat in categories:
        category = cat.lower()
        # Performance: O(1) dict lookup instead of if/elif chain
        if category in category_mapping:
            symbols_to_fetch.extend(category_mapping[category])
        elif category in MARKET_SYMBOLS:
            # Check if it's a specific symbol key
            symbols_to_fetch.append(category)

    # Fetch data for each symbol
    # Performance: Dict comprehension with filter (single pass)
    return {
        key: get_ticker_data(symbol)
        for key in symbols_to_fetch
        if (symbol := MARKET_SYMBOLS.get(key)) is not None
    }


def get_ticker_history(symbol: str, period: str = "1mo") -> dict[str, Any]:
    """Get historical price data for a ticker"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return {"error": f"No historical data found for {symbol}"}

        return {
            "symbol": symbol,
            "period": period,
            "data": hist.to_dict("records"),
            "start_date": hist.index[0].isoformat(),
            "end_date": hist.index[-1].isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


def format_market_snapshot(data: dict[str, dict[str, Any]]) -> str:
    """Format market data into concise readable text (BBG Lite style)"""
    now = datetime.now(ZoneInfo("America/New_York"))
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    tz_str = now.strftime("%Z")
    market_status = "During market" if is_market_open() else "After-hours"

    # Header
    lines = [f"MARKETS {date_str} | {market_status}"]

    for section_name, symbols in FORMATTING_SECTIONS.items():
        # Check if any symbols in this section are in our data
        section_data = {k: v for k, v in data.items() if k in symbols}
        if not section_data:
            continue

        lines.append(section_name)
        for symbol, info in section_data.items():
            if info.get("error"):
                display_name = DISPLAY_NAMES.get(symbol, symbol)
                lines.append(f"{display_name:12} ERROR - {info['error']}")
            else:
                price = info.get("price")
                change_pct = info.get("change_percent")

                if price is not None and change_pct is not None:
                    display_name = DISPLAY_NAMES.get(symbol, symbol)
                    annotation = FACTOR_ANNOTATIONS.get(symbol, "")
                    # Add annotation if present
                    if annotation:
                        line = f"{display_name:12} {price:10.2f}  {change_pct:+6.2f}%  {annotation}"
                        lines.append(line)
                    else:
                        lines.append(f"{display_name:12} {price:10.2f}  {change_pct:+6.2f}%")
                elif price is not None:
                    display_name = DISPLAY_NAMES.get(symbol, symbol)
                    lines.append(f"{display_name:12} {price:10.2f}")
                else:
                    display_name = DISPLAY_NAMES.get(symbol, symbol)
                    lines.append(f"{display_name:12} N/A")
        lines.append("")  # blank line between sections

    # Footer with guidance
    lines.append(f"Data as of {date_str} {time_str} {tz_str} | Source: yfinance")
    lines.append(
        "Try: symbol='TSLA' for ticker | categories=['europe'] for regions | "
        "period='3mo' for history"
    )

    return "\n".join(lines)
