# yfinance MCP Server

Model Context Protocol server for Yahoo Finance market data.

## Features

- **Market snapshots** - Quick overview of futures, indices, crypto, commodities
- **Smart defaults** - Automatically shows futures (after hours) or indices (market hours)
- **Single ticker queries** - Get current price for any stock
- **Historical data** - Fetch price history for analysis
- **Human-readable output** - Formatted for immediate use, not raw JSON

## Installation

```bash
cd /home/ubuntu/idio/yfinance-mcp
poetry install
```

## Configuration

Add to `~/.config/claude/mcp.json`:

```json
{
  "mcpServers": {
    "yfinance": {
      "command": "poetry",
      "args": ["run", "python", "server.py"],
      "cwd": "/home/ubuntu/idio/yfinance-mcp"
    }
  }
}
```

Restart Claude Code to load the MCP server.

## Usage

### Market Snapshot (Auto)

No parameters needed - automatically shows relevant data based on time:

```python
mcp__yfinance__get_market_data()
```

**During market hours** (9:30 AM - 4:00 PM ET, Mon-Fri):
- US indices (S&P 500, Nasdaq, Dow)
- Crypto (Bitcoin, Ethereum)
- Commodities (Gold, Oil WTI, Natural Gas)

**After hours:**
- US futures (ES, NQ, YM)
- Crypto (Bitcoin, Ethereum)
- Commodities (Gold, Oil WTI, Natural Gas)

### Market Snapshot (Custom)

Specify which categories to show:

```python
mcp__yfinance__get_market_data(
    data_type='snapshot',
    categories=['futures', 'europe', 'asia', 'crypto']
)
```

**Available categories:**
- `us` - S&P 500, Nasdaq, Dow (cash indices)
- `futures` - ES, NQ, YM futures contracts
- `europe` - STOXX 50, DAX, FTSE
- `asia` - Nikkei, Hang Seng, Shanghai
- `crypto` - Bitcoin, Ethereum
- `commodities` - Gold, Oil WTI, Natural Gas
- `all` - Everything

### Single Ticker

Get current price for any stock:

```python
mcp__yfinance__get_market_data(
    data_type='current',
    symbol='AAPL'
)
```

### Historical Data

Fetch price history:

```python
mcp__yfinance__get_market_data(
    data_type='history',
    symbol='TSLA',
    period='3mo'
)
```

**Available periods:** `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `max`

## Output Format

Market snapshot output:

```
=== MARKETS - October 16, 2025 ===

US FUTURES:
S&P 500       6733.00 (+0.27%)
Nasdaq       25089.50 (+0.66%)
Dow          46568.00 (+0.16%)

CRYPTO:
Bitcoin      $111494.80 (+0.63%)
Ethereum     $ 4066.60 (+1.99%)

COMMODITIES:
Gold         $ 4267.70 (+1.57%)
Oil WTI      $   58.02 (+0.31%)
Nat Gas      $    3.01 (-0.20%)
```

Clean, readable, immediately useful.

## Development

See `CLAUDE.md` for design philosophy, development process, and methodology.

## License

MIT
