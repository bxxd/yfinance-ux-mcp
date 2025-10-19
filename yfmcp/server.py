#!/usr/bin/env python3
"""
yfinance MCP Server - MCP protocol wrapper

UI-based screens (not API endpoints):
- markets() - Market overview with all factors
- sector(name) - Sector drill-down (TODO)
- ticker(symbol) - Individual security (TODO)

Core business logic in market_data.py (testable independently)
This file handles MCP protocol layer only
"""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .market_data import format_markets, get_markets_data

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
    ]


@app.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: Any) -> list[TextContent]:  # noqa: ANN401
    """Handle tool execution - thin wrapper around core business logic"""
    if name == "markets":
        data = get_markets_data()
        formatted = format_markets(data)
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
