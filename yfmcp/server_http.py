#!/usr/bin/env python3
"""
yfinance MCP Server - HTTP/SSE transport

Network server for multi-tenant Claude Code access.
Same MCP protocol as stdio server, different transport.

Run with: make server

Configuration:
- PORT: Server port (default: 5001)
"""

import os
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from .market_data import (
    format_markets,
    format_sector,
    format_ticker,
    format_ticker_batch,
    get_markets_data,
    get_sector_data,
    get_ticker_screen_data,
)

# Configuration
DEFAULT_PORT = 5001


def get_port() -> int:
    """Get server port from environment or use default"""
    port_str = os.environ.get("PORT", str(DEFAULT_PORT))
    try:
        return int(port_str)
    except ValueError:
        msg = f"Invalid PORT value: {port_str}"
        raise ValueError(msg) from None


# MCP Server instance (reuses same logic as stdio server)
mcp_server = Server("yfinance-mcp")

# SSE transport for multi-client support
sse_transport = SseServerTransport("/messages")


@mcp_server.list_tools()  # type: ignore[misc,no-untyped-call]
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


@mcp_server.call_tool()  # type: ignore[misc]
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
            # Batch comparison mode
            data_list = [get_ticker_screen_data(sym) for sym in symbol]
            formatted = format_ticker_batch(data_list)
            return [TextContent(type="text", text=formatted)]

        # Single ticker mode
        data = get_ticker_screen_data(symbol)
        formatted = format_ticker(data)
        return [TextContent(type="text", text=formatted)]

    msg = f"Unknown tool: {name}"
    raise ValueError(msg)


# Starlette endpoint handlers

async def handle_ping(_request: Request) -> JSONResponse:
    """Health check endpoint"""
    return JSONResponse({"status": "ok"})


async def handle_sse(request: Request) -> Response:
    """
    SSE endpoint for MCP protocol.

    Creates a new SSE connection for each client, runs the MCP server
    with the connection streams, and returns when client disconnects.
    """
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )
    # Return empty response to avoid NoneType error (per MCP docs)
    return Response()


# Simple REST endpoints (convenience layer, MCP is primary)


async def handle_rest_markets(_request: Request) -> Response:
    """REST endpoint for markets() - returns BBG Lite text"""
    try:
        data = get_markets_data()
        formatted = format_markets(data)
        return Response(content=formatted, media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(
            content=f"Error: {e!s}", status_code=500, media_type="text/plain"
        )


async def handle_rest_sector(request: Request) -> Response:
    """REST endpoint for sector() - returns BBG Lite text"""
    name = request.query_params.get("name", "")
    if not name:
        return Response(
            content="Missing 'name' parameter", status_code=400, media_type="text/plain"
        )

    try:
        data = get_sector_data(name)
        formatted = format_sector(data)
        return Response(content=formatted, media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(
            content=f"Error: {e!s}", status_code=500, media_type="text/plain"
        )


async def handle_rest_ticker(request: Request) -> Response:
    """REST endpoint for ticker() - returns BBG Lite text"""
    symbol = request.query_params.get("symbol", "")
    if not symbol:
        return Response(
            content="Missing 'symbol' parameter",
            status_code=400,
            media_type="text/plain",
        )

    try:
        data = get_ticker_screen_data(symbol)
        formatted = format_ticker(data)
        return Response(content=formatted, media_type="text/plain; charset=utf-8")
    except Exception as e:
        return Response(
            content=f"Error: {e!s}", status_code=500, media_type="text/plain"
        )


# Starlette application
app = Starlette(
    routes=[
        Route("/ping", endpoint=handle_ping, methods=["GET"]),
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/messages", app=sse_transport.handle_post_message),
        # REST convenience endpoints (MCP is primary)
        Route("/api/markets", endpoint=handle_rest_markets, methods=["GET"]),
        Route("/api/sector", endpoint=handle_rest_sector, methods=["GET"]),
        Route("/api/ticker", endpoint=handle_rest_ticker, methods=["GET"]),
    ]
)
