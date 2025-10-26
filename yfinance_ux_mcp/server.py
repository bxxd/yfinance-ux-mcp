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
    format_sector,
    format_ticker,
    format_ticker_batch,
    get_markets_data,
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
