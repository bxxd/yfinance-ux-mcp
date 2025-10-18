#!/usr/bin/env python3
"""
yfinance MCP Server - MCP protocol wrapper
Provides single flexible market data tool to minimize context usage

Core business logic in market_data.py (testable independently)
This file handles MCP protocol layer only
"""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .market_data import (
    format_market_snapshot,
    get_market_snapshot,
    get_ticker_data,
    get_ticker_history,
)

app = Server("yfinance-mcp")


@app.list_tools()  # type: ignore[misc,no-untyped-call]
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="get_market_data",
            description="""
Yahoo Finance market data tool. Supports snapshots, current prices, and historical data.

Output organized by Paleologo factor framework: broad market, risk factors, commodities, rates.

Examples:
- Auto-detect: {} (shows factors + market indices)
- Factor view: {"data_type": "snapshot", "categories": ["futures", "factors"]}
- Current price: {"data_type": "current", "symbol": "AAPL"}
- Historical: {"data_type": "history", "symbol": "TSLA", "period": "3mo"}

Use standard Yahoo tickers (e.g., AAPL, ^GSPC, BTC-USD). Output: Formatted text for easy scanning.
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "data_type": {
                        "type": "string",
                        "enum": ["snapshot", "current", "history"],
                        "description": "Data type",
                        "default": "snapshot"
                    },
                    "categories": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "us", "futures", "factors", "europe", "asia",
                                "crypto", "commodities", "bonds", "all"
                            ]
                        },
                        "description": "Market categories (for snapshot only)"
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Ticker symbol (required for current/history)"
                    },
                    "period": {
                        "type": "string",
                        "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"],
                        "description": "Time period (for history only)",
                        "default": "1mo"
                    }
                },
                "required": []
            }
        ),
    ]


@app.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: Any) -> list[TextContent]:  # noqa: ANN401
    """Handle tool execution - thin wrapper around core business logic"""
    if name != "get_market_data":
        msg = f"Unknown tool: {name}"
        raise ValueError(msg)

    data_type = arguments.get("data_type", "snapshot")

    if data_type == "snapshot":
        categories = arguments.get("categories", [])
        data = get_market_snapshot(categories)
        formatted = format_market_snapshot(data)
        return [TextContent(type="text", text=formatted)]

    if data_type == "current":
        symbol = arguments.get("symbol")
        if not symbol:
            return [TextContent(type="text", text="Error: symbol required for current data")]

        data = get_ticker_data(symbol)
        return [TextContent(type="text", text=json.dumps(data, indent=2))]

    # data_type == "history" (only remaining option per inputSchema enum)
    symbol = arguments.get("symbol")
    period = arguments.get("period", "1mo")
    if not symbol:
        return [TextContent(type="text", text="Error: symbol required for historical data")]

    data = get_ticker_history(symbol, period)
    return [TextContent(type="text", text=json.dumps(data, indent=2))]


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
