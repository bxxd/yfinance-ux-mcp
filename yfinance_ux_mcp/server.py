#!/usr/bin/env python3
"""
yfinance MCP Server - MCP protocol wrapper

UI-based screens (not API endpoints):
- markets() - Market overview with all factors
- sector(name) - Sector drill-down
- ticker(symbol) - Individual security

Core business logic in market_data.py (testable independently)
This file handles MCP protocol layer only
"""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .market_data import (
    format_markets,
    format_news,
    format_options,
    format_sector,
    format_ticker,
    format_ticker_batch,
    get_markets_data,
    get_news_data,
    get_options_data,
    get_sector_data,
    get_ticker_screen_data,
    get_ticker_screen_data_batch,
)

app = Server("yfinance-mcp")


@app.list_tools()  # type: ignore[misc,no-untyped-call]
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="markets",
            description="""
Market overview screen - complete factor landscape.

Shows:
- US EQUITIES (S&P 500, Nasdaq, Dow, Russell 2000)
- GLOBAL (Europe, Asia, China)
- SECTORS (all 11 GICS sectors with momentum)
- STYLES (Momentum, Value, Growth, Quality, Size)
- COMMODITIES (Gold, Oil, Natural Gas)
- VOLATILITY & RATES (VIX, 10Y Treasury)

All with momentum (1M, 1Y trailing returns).

Output: BBG Lite formatted text (dense, scannable, professional).

Navigation: Drill down with sector('technology') or ticker('AAPL')
""",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="sector",
            description="""
Sector drill-down screen - detailed sector analysis.

Shows:
- Sector ETF price and momentum (1M, 1Y)
- Top 10 holdings with symbol, name, and weight
- Navigation back to markets() or drill to ticker()

Input: Sector name (e.g., 'technology', 'real estate', 'financials')

Accepts both display names and normalized names:
- 'technology' or 'tech'
- 'real estate' or 'real_estate'
- 'consumer discretionary' or 'consumer_disc'
- 'consumer staples' or 'consumer_stpl'

Output: BBG Lite formatted text (dense, scannable, professional).
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "Sector name (e.g., 'technology', 'financials', "
                            "'healthcare', 'energy', 'consumer discretionary', "
                            "'consumer staples', 'industrials', 'utilities', "
                            "'materials', 'real estate', 'communication')"
                        ),
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="ticker",
            description="""
Individual security screen - complete factor analysis.

SINGLE TICKER MODE:
Input: symbol as string (e.g., 'TSLA')
Shows: Detailed analysis with full factor exposures, valuation, technicals

BATCH COMPARISON MODE:
Input: symbol as array of strings (e.g., ['TSLA', 'F', 'GM'])
Shows: Side-by-side comparison table with key factors

Example output for ticker('TSLA'):

TICKER TSLA

LAST PRICE  460.55 +8.13  +1.80%

Tesla, Inc.                              MKT CAP  1531.7B    VOLUME  79.8M

FACTOR EXPOSURES
Beta (SPX)       2.09    (High sensitivity)
Idio Vol         49.9%   (High stock-specific risk)
Total Vol        67.9%

VALUATION
P/E Ratio        317.62
Forward P/E      142.15

CALENDAR
Earnings         Oct 22, 2025  (Est $0.44 EPS)

MOMENTUM & TECHNICALS
1-Month            +3.9%
1-Year            +75.4%
50-Day MA         400.44
200-Day MA        336.07
RSI (14D)         57.5

52-WEEK RANGE
High              488.54
Low               214.25
Current           460.55  [=================░░░]  90% of range

RECENT NEWS (5 of 10+ articles, see all: news('TSLA'))
[10-28] Nvidia, Lucid team up for true autonomous driving in future vehicles
[10-27] Tesla 'may lose' Elon Musk if shareholders don't approve $1 trillion...
[10-29] Dow Jones, S&P 500 Hit Highs; Why Microsoft, Google, Meta Earnings ...

For full news: news('TSLA')
For options analysis: options('TSLA')

Output: BBG Lite formatted text (dense, scannable, professional).
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}}
                        ],
                        "description": (
                            "Ticker symbol or list of symbols "
                            "(e.g., 'TSLA' or ['TSLA', 'F', 'GM'])"
                        ),
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="news",
            description="""
News screen - recent articles for a ticker.

Shows:
- All available news articles (typically 10)
- Full headlines with timestamps
- Article summaries (1-2 sentences)
- Source attribution (Yahoo Finance, Reuters, Bloomberg, etc.)
- Read URLs for full articles

Input: symbol as string (e.g., 'TSLA')

Output: BBG Lite formatted text with progressive disclosure.

Navigation: Back to ticker('TSLA') for price/factor data
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'TSLA', 'AAPL')",
                    }
                },
                "required": ["symbol"]
            }
        ),
        Tool(
            name="options",
            description="""
Options chain analysis screen - positioning, IV structure, vol skew, term structure.

Shows:
- Positioning: Put/Call ratio (OI, volume), sentiment (bullish/bearish/neutral)
- Top strikes: Largest OI positions for calls and puts
- IV structure: ATM IV for calls/puts, spread (unusual patterns)
- Vol skew: OTM vs ATM (panic premium detection)
- Term structure: Near/mid/far IV, contango (compression expectations)
- Interpretation: Context insights (NO recommendations)

Input:
- symbol: Ticker symbol (e.g., 'PALL', 'AAPL')
- expiration (optional): 'nearest' (default) or specific date like '2025-12-20'

Example output for options('PALL'):

PALL US EQUITY                          OPTIONS ANALYSIS
Last: $127.88                          Exp: 2025-11-21 (23d)  |  ATM: $130

POSITIONING (Open Interest)
Calls:  4,598 OI
Puts:   2,617 OI
P/C Ratio:  0.57    ← BULLISH (calls 1.8x puts)

TOP POSITIONS BY STRIKE
CALLS                                   PUTS
Strike    OI     Last      IV          Strike    OI     Last      IV
────────────────────────────────────   ──────────────────────────────────────
$160    1,173    $ 1.07     60.8%       $115      494    $ 2.04     50.8%
$150      898    $ 1.81     63.5%       $116      451    $ 2.63     50.4%

IMPLIED VOLATILITY
ATM Calls:     55.5%
ATM Puts:      51.5%
Spread:        +4.0% calls  ← UNUSUAL (calls typically lower)

VOL SKEW
OTM Puts vs ATM:  +5.5%
OTM Calls vs ATM: +13.0%

TERM STRUCTURE
Near (23d):    55.5%       ← Current
Mid (51d):    53.8%
Far (142d):    47.5%
Contango:     +8.0%       ← Market expects compression (to 47.5%)

INTERPRETATION
• Heavy call positioning: OI P/C 0.57 (1.8x calls vs puts)
• Calls IV elevated: 4.0% above puts
• Term structure contango: market pricing vol compression from 55.5% → 47.5%

Output: BBG Lite formatted text (dense, scannable, professional).
Context delivery system - NO recommendations.

Navigation: Back to ticker('PALL') for price/factor data
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (e.g., 'PALL', 'AAPL')",
                    },
                    "expiration": {
                        "type": "string",
                        "description": "Expiration date: 'nearest' (default) or 'YYYY-MM-DD'",
                        "default": "nearest",
                    }
                },
                "required": ["symbol"]
            }
        ),
    ]


@app.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: Any) -> list[TextContent]:  # noqa: ANN401
    """Handle tool execution - thin wrapper around core business logic"""
    if name == "markets":
        data = get_markets_data()
        formatted = format_markets(data)
        return [TextContent(type="text", text=formatted)]

    if name == "sector":
        sector_name = arguments.get("name")
        if not sector_name:
            msg = "sector() requires 'name' parameter"
            raise ValueError(msg)
        data = get_sector_data(sector_name)
        formatted = format_sector(data)
        return [TextContent(type="text", text=formatted)]

    if name == "ticker":
        symbol = arguments.get("symbol")
        if not symbol:
            msg = "ticker() requires 'symbol' parameter"
            raise ValueError(msg)

        # Check if batch mode (list) or single mode (string)
        if isinstance(symbol, list):
            # Batch comparison mode - use batch API to avoid hammering Yahoo
            data_list = get_ticker_screen_data_batch(symbol)
            formatted = format_ticker_batch(data_list)
            return [TextContent(type="text", text=formatted)]

        # Single ticker mode
        data = get_ticker_screen_data(symbol)
        formatted = format_ticker(data)
        return [TextContent(type="text", text=formatted)]

    if name == "news":
        symbol = arguments.get("symbol")
        if not symbol:
            msg = "news() requires 'symbol' parameter"
            raise ValueError(msg)
        data = get_news_data(symbol)
        formatted = format_news(data)
        return [TextContent(type="text", text=formatted)]

    if name == "options":
        symbol = arguments.get("symbol")
        if not symbol:
            msg = "options() requires 'symbol' parameter"
            raise ValueError(msg)
        expiration = arguments.get("expiration", "nearest")
        data = get_options_data(symbol, expiration)
        formatted = format_options(data)
        return [TextContent(type="text", text=formatted)]

    msg = f"Unknown tool: {name}"
    raise ValueError(msg)


async def main() -> None:
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
