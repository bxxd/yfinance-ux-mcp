"""
yfinance_fetcher - Reliable yfinance data fetching

ONE SOURCE OF TRUTH: mcp-yfinance-ux/lib/yfinance_fetcher.py

Battle-tested code from MCP server production use.
NO dependencies on MCP server infrastructure.

Pattern: Individual yf.Ticker().history() with ThreadPoolExecutor (RELIABLE)
         NOT yf.download() batch API (UNRELIABLE - timeouts)
"""

from yfinance_fetcher import (
    normalize_symbol,
    calculate_date_range,
    fetch_price_history,
    fetch_multiple_histories,
    fetch_ticker_and_market,
    fetch_price_at_date,
)

__all__ = [
    "normalize_symbol",
    "calculate_date_range",
    "fetch_price_history",
    "fetch_multiple_histories",
    "fetch_ticker_and_market",
    "fetch_price_at_date",
]
