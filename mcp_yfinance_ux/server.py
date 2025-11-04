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
    format_options,
    format_sector,
    format_ticker,
    format_ticker_batch,
    get_markets_data,
    get_options_data,
    get_sector_data,
    get_ticker_screen_data,
    get_ticker_screen_data_batch,
)
from .tools import get_mcp_tools

app = Server("yfinance-mcp")


@app.list_tools()  # type: ignore[misc,no-untyped-call]
async def list_tools() -> list[Tool]:
    """List available MCP tools - imported from tools.py (single source of truth)"""
    return get_mcp_tools()




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

    if name == "ticker_options":
        symbol = arguments.get("symbol")
        if not symbol:
            msg = "ticker_options() requires 'symbol' parameter"
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
