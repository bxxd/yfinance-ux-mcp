#!/usr/bin/env python3
"""
CLI wrapper for yfinance MCP server - shows exactly what Claude sees

Zero drift: Uses actual MCP server handlers for tool listing and execution.

Usage:
  ./cli.py list-tools              # Show available tools (what Claude sees)
  ./cli.py call [tool] [args]      # Call a tool (what Claude receives)

Examples:
  ./cli.py list-tools
  ./cli.py call get_market_data
  ./cli.py call get_market_data --data_type snapshot --categories futures,crypto
  ./cli.py call get_market_data --data_type current --symbol TSLA
"""

import argparse
import asyncio
import json
import sys
import traceback
from typing import Any

from .server import call_tool, list_tools


async def list_tools_command() -> None:
    """Show available tools exactly as Claude sees them - no drift"""
    # Call the actual MCP list_tools handler
    tools = await list_tools()

    print("=" * 80)
    print("AVAILABLE TOOLS (what Claude sees)")
    print("=" * 80)
    print()

    for tool in tools:
        print(f"Server name: {tool.name}")
        print(f"Claude sees: mcp__idio_yf__{tool.name}")
        print()
        print(f"Description:{tool.description}")
        print()
        print("Input Schema:")
        print(json.dumps(tool.inputSchema, indent=2))
        print()


async def call_tool_command(tool_name: str, args: dict[str, Any]) -> int:
    """Call a tool and show output exactly as Claude receives it - no drift"""
    print("=" * 80)
    print(f"CALLING TOOL: {tool_name}")
    print("=" * 80)
    print()
    print("Arguments:")
    print(json.dumps(args, indent=2))
    print()
    print("-" * 80)
    print("OUTPUT (what Claude receives):")
    print("-" * 80)
    print()

    try:
        # Call the actual MCP call_tool handler
        results = await call_tool(tool_name, args)
        for result in results:
            if hasattr(result, "text"):
                print(result.text)
            else:
                print(result)
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        return 1

    return 0


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="CLI wrapper for yfinance MCP - see what Claude sees",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list-tools
  %(prog)s call get_market_data
  %(prog)s call get_market_data --data_type snapshot --categories futures,crypto
  %(prog)s call get_market_data --data_type current --symbol TSLA
  %(prog)s call get_market_data --data_type history --symbol AAPL --period 3mo
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list-tools command
    subparsers.add_parser("list-tools", help="Show available tools")

    # call command
    call_parser = subparsers.add_parser("call", help="Call a tool")
    call_parser.add_argument("tool", help="Tool name to call")
    call_parser.add_argument("--data_type", help="Data type: snapshot, current, history")
    call_parser.add_argument(
        "--categories", help="Comma-separated categories (e.g., futures,crypto)"
    )
    call_parser.add_argument("--symbol", help="Ticker symbol (e.g., TSLA, AAPL)")
    call_parser.add_argument("--period", help="Period for history (e.g., 1mo, 3mo, 1y)")
    call_parser.add_argument(
        "--show_momentum",
        action="store_true",
        help="Show trailing returns (1M, 1Y) for momentum analysis"
    )

    return parser.parse_args()


async def main() -> int:
    args = parse_args()

    if not args.command:
        print("Error: No command specified")
        print("Usage: ./cli.py list-tools | call <tool> [args]")
        return 1

    if args.command == "list-tools":
        await list_tools_command()
        return 0

    # args.command == "call" (only remaining option per argparse subparsers)
    # Build tool arguments
    tool_args = {}
    if args.data_type:
        tool_args["data_type"] = args.data_type
    if args.categories:
        tool_args["categories"] = args.categories.split(",")
    if args.symbol:
        tool_args["symbol"] = args.symbol
    if args.period:
        tool_args["period"] = args.period
    if args.show_momentum:
        tool_args["show_momentum"] = True

    return await call_tool_command(args.tool, tool_args)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
