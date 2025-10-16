#!/usr/bin/env python3
"""
yfinance MCP Server - Custom implementation for idio project
Provides single flexible market data tool to minimize context usage
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from zoneinfo import ZoneInfo

import yfinance as yf
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

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
}

app = Server("yfinance-mcp")


def is_market_open() -> bool:
    """Check if US market is currently open (9:30 AM - 4:00 PM ET, Mon-Fri)"""
    now_et = datetime.now(ZoneInfo("America/New_York"))

    # Check if weekend
    if now_et.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False

    # Check if within market hours (9:30 AM - 4:00 PM ET)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now_et < market_close


def format_market_snapshot(data: dict) -> str:
    """Format market data into concise readable text"""
    from datetime import datetime

    # Header with date
    lines = [f"=== MARKETS - {datetime.now().strftime('%B %d, %Y')} ===", ""]

    # Group symbols by category - order matches manual code
    sections = {
        'US FUTURES': ['es_futures', 'nq_futures', 'ym_futures'],
        'CRYPTO': ['btc', 'eth'],
        'COMMODITIES': ['gold', 'oil_wti', 'natgas'],
        'US INDICES': ['sp500', 'nasdaq', 'dow'],
        'EUROPE': ['stoxx50', 'dax', 'ftse'],
        'ASIA': ['nikkei', 'hangseng', 'shanghai'],
    }

    # Friendly names
    names = {
        'es_futures': 'S&P 500', 'nq_futures': 'Nasdaq', 'ym_futures': 'Dow',
        'btc': 'Bitcoin', 'eth': 'Ethereum',
        'gold': 'Gold', 'oil_wti': 'Oil WTI', 'natgas': 'Nat Gas',
        'sp500': 'S&P 500', 'nasdaq': 'Nasdaq', 'dow': 'Dow',
        'stoxx50': 'STOXX 50', 'dax': 'DAX', 'ftse': 'FTSE',
        'nikkei': 'Nikkei', 'hangseng': 'Hang Seng', 'shanghai': 'Shanghai',
    }

    for section_name, symbols in sections.items():
        # Check if any symbols in this section are in our data
        section_data = {k: v for k, v in data.items() if k in symbols}
        if not section_data:
            continue

        lines.append(f"{section_name}:")
        for symbol, info in section_data.items():
            if info.get("error"):
                lines.append(f"{names.get(symbol, symbol):12} ERROR - {info['error']}")
            else:
                price = info.get('price')
                change_pct = info.get('change_percent')

                if price is not None and change_pct is not None:
                    name = names.get(symbol, symbol)

                    # Crypto and commodities get $
                    if symbol in ['btc', 'eth', 'gold', 'oil_wti', 'natgas']:
                        lines.append(f"{name:12} ${price:8.2f} ({change_pct:+.2f}%)")
                    # Futures and indices: no $
                    else:
                        lines.append(f"{name:12} {price:8.2f} ({change_pct:+.2f}%)")
                elif price is not None:
                    lines.append(f"{names.get(symbol, symbol):12} {price:8.2f}")
                else:
                    lines.append(f"{names.get(symbol, symbol):12} N/A")
        lines.append("")  # blank line between sections

    return "\n".join(lines)


def get_ticker_data(symbol: str) -> dict:
    """Fetch current data for a single ticker"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        price = info.get('regularMarketPrice') or info.get('currentPrice')
        change_pct = info.get('regularMarketChangePercent')

        return {
            "symbol": symbol,
            "price": price,
            "change_percent": change_pct,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def get_market_snapshot(categories: list[str]) -> dict:
    """Get snapshot of multiple market categories"""
    result = {}
    symbols_to_fetch = []

    # Auto-detect: if no categories specified, show smart default
    if not categories:
        if is_market_open():
            categories = ["us", "crypto", "commodities"]
        else:
            categories = ["futures", "crypto", "commodities"]

    # Build symbol list based on categories - matches manual code sections
    for category in categories:
        category = category.lower()
        if category == "us":
            symbols_to_fetch.extend(["sp500", "nasdaq", "dow"])
        elif category == "futures":
            symbols_to_fetch.extend(["es_futures", "nq_futures", "ym_futures"])
        elif category == "europe":
            symbols_to_fetch.extend(["stoxx50", "dax", "ftse"])
        elif category == "asia":
            symbols_to_fetch.extend(["nikkei", "hangseng", "shanghai"])
        elif category == "crypto":
            symbols_to_fetch.extend(["btc", "eth"])
        elif category == "commodities":
            symbols_to_fetch.extend(["gold", "oil_wti", "natgas"])
        elif category == "all":
            symbols_to_fetch.extend(["es_futures", "nq_futures", "ym_futures",
                                     "btc", "eth",
                                     "gold", "oil_wti", "natgas",
                                     "sp500", "nasdaq", "dow",
                                     "stoxx50", "dax", "ftse",
                                     "nikkei", "hangseng", "shanghai"])
        else:
            # Check if it's a specific symbol key
            if category in MARKET_SYMBOLS:
                symbols_to_fetch.append(category)

    # Fetch data for each symbol
    for key in symbols_to_fetch:
        symbol = MARKET_SYMBOLS.get(key)
        if symbol:
            result[key] = get_ticker_data(symbol)

    return result


def get_ticker_history(symbol: str, period: str = "1mo") -> dict:
    """Get historical price data for a ticker"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return {"error": f"No historical data found for {symbol}"}

        return {
            "symbol": symbol,
            "period": period,
            "data": hist.to_dict('records'),
            "start_date": hist.index[0].isoformat(),
            "end_date": hist.index[-1].isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="get_market_data",
            description="""
Get market data from Yahoo Finance. Single flexible tool to minimize context usage.

Supports multiple data types:
- Market snapshots: categories=['us', 'futures', 'europe', 'crypto', 'commodities']
- Single ticker: symbol='AAPL', data_type='current'
- Historical data: symbol='TSLA', data_type='history', period='1mo'
- Custom symbols: Use standard Yahoo Finance tickers

Examples:
1. Morning market check: categories=['futures', 'crypto', 'commodities']
2. Stock price: symbol='AAPL', data_type='current'
3. Historical: symbol='SPY', data_type='history', period='3mo'
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "data_type": {
                        "type": "string",
                        "enum": ["snapshot", "current", "history"],
                        "description": "Type of data to fetch",
                        "default": "snapshot"
                    },
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Market categories for snapshot: us, futures, europe, asia, crypto, commodities, bonds, all"
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol for current/history queries (e.g., 'AAPL', 'TSLA')"
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period for historical data: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max",
                        "default": "1mo"
                    }
                },
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool execution"""
    if name != "get_market_data":
        raise ValueError(f"Unknown tool: {name}")

    data_type = arguments.get("data_type", "snapshot")

    if data_type == "snapshot":
        categories = arguments.get("categories", [])
        data = get_market_snapshot(categories)
        formatted = format_market_snapshot(data)
        return [TextContent(type="text", text=formatted)]

    elif data_type == "current":
        symbol = arguments.get("symbol")
        if not symbol:
            return [TextContent(type="text", text="Error: symbol required for current data")]

        data = get_ticker_data(symbol)
        return [TextContent(type="text", text=json.dumps(data, indent=2))]

    elif data_type == "history":
        symbol = arguments.get("symbol")
        period = arguments.get("period", "1mo")
        if not symbol:
            return [TextContent(type="text", text="Error: symbol required for historical data")]

        data = get_ticker_history(symbol, period)
        return [TextContent(type="text", text=json.dumps(data, indent=2))]

    else:
        return [TextContent(type="text", text=f"Error: Unknown data_type '{data_type}'")]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
