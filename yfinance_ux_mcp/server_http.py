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
import signal
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
from .tools import get_mcp_tools

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
    """List available MCP tools - imported from tools.py (single source of truth)"""
    return get_mcp_tools()




@mcp_server.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: Any) -> list[TextContent]:  # noqa: ANN401
    """Handle tool execution - thin wrapper around core business logic"""
    print(f"[MCP-SERVER] call_tool: name={name}, arguments={arguments}", flush=True)

    if name == "markets":
        data = get_markets_data()
        formatted = format_markets(data)
        print(f"[MCP-SERVER] markets() returning {len(formatted)} chars", flush=True)
        return [TextContent(type="text", text=formatted)]

    if name == "sector":
        sector_name = arguments.get("name")
        if not sector_name:
            msg = "sector() requires 'name' parameter"
            raise ValueError(msg)
        data = get_sector_data(sector_name)
        formatted = format_sector(data)
        print(f"[MCP-SERVER] sector({sector_name}) returning {len(formatted)} chars", flush=True)
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
            print(
                f"[MCP-SERVER] ticker({symbol}) batch returning {len(formatted)} chars",
                flush=True
            )
            return [TextContent(type="text", text=formatted)]

        # Single ticker mode
        data = get_ticker_screen_data(symbol)
        formatted = format_ticker(data)
        print(f"[MCP-SERVER] ticker({symbol}) returning {len(formatted)} chars", flush=True)
        return [TextContent(type="text", text=formatted)]

    if name == "ticker_news":
        symbol = arguments.get("symbol")
        if not symbol:
            msg = "ticker_news() requires 'symbol' parameter"
            raise ValueError(msg)
        data = get_news_data(symbol)
        formatted = format_news(data)
        print(f"[MCP-SERVER] ticker_news({symbol}) returning {len(formatted)} chars", flush=True)
        return [TextContent(type="text", text=formatted)]

    if name == "ticker_options":
        symbol = arguments.get("symbol")
        if not symbol:
            msg = "ticker_options() requires 'symbol' parameter"
            raise ValueError(msg)
        expiration = arguments.get("expiration", "nearest")
        data = get_options_data(symbol, expiration)
        formatted = format_options(data)
        print(
            f"[MCP-SERVER] ticker_options({symbol}, {expiration}) returning {len(formatted)} chars",
            flush=True
        )
        return [TextContent(type="text", text=formatted)]

    msg = f"Unknown tool: {name}"
    raise ValueError(msg)


# Starlette endpoint handlers

async def handle_ping(_request: Request) -> JSONResponse:
    """Health check endpoint"""
    return JSONResponse({"status": "ok"})


async def handle_shutdown(_request: Request) -> JSONResponse:
    """Graceful shutdown endpoint"""
    # Send SIGTERM to self for graceful shutdown
    os.kill(os.getpid(), signal.SIGTERM)
    return JSONResponse({"status": "shutting down"})


async def handle_sse(request: Request) -> Response:
    """
    SSE endpoint for MCP protocol.

    Creates a new SSE connection for each client, runs the MCP server
    with the connection streams, and returns when client disconnects.
    """
    client_addr = request.client.host if request.client else "unknown"
    print(f"[MCP-SERVER] New SSE connection from {client_addr}", flush=True)

    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        print("[MCP-SERVER] SSE connected, running MCP server loop", flush=True)
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )
        print(f"[MCP-SERVER] SSE disconnected from {client_addr}", flush=True)

    # Return empty response to avoid NoneType error (per MCP docs)
    # Add cache headers: 10 seconds for market data (5-10s range)
    return Response(
        headers={
            "Cache-Control": "public, max-age=10, must-revalidate",
            "X-Content-Type-Options": "nosniff",
        }
    )


# Starlette application
app = Starlette(
    routes=[
        Route("/ping", endpoint=handle_ping, methods=["GET"]),
        Route("/shutdown", endpoint=handle_shutdown, methods=["POST"]),
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/messages", app=sse_transport.handle_post_message),
    ]
)
