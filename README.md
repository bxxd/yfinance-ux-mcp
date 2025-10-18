# idio-yfinance-mcp

Market data tools for idiosyncratic alpha analysis. Powered by yfinance.

**Local MCP server (stdio)** - Runs locally on your machine, connects to Claude Code via standard I/O.

Provides fast access to market snapshots, price data, and historical analysis.

## Features

- **Market snapshots** - Quick overview of futures, indices, crypto, commodities
- **Smart defaults** - Automatically shows futures (after hours) or indices (market hours)
- **Single ticker queries** - Get current price for any stock
- **Historical data** - Fetch price history for analysis
- **Human-readable output** - Formatted for immediate use, not raw JSON

## Installation

### 1. Clone and install dependencies

```bash
git clone https://github.com/bxxd/idio-yfinance-mcp.git
cd idio-yfinance-mcp
poetry install
```

### 2. Configure Claude Code

**Note:** This is a local stdio MCP server. It runs on your machine and connects to Claude Code via standard I/O (not HTTP/network). All data stays local.

**Method 1: Using make -C (recommended)**

From your project directory:

```bash
claude mcp add idio-yf make -C /absolute/path/to/yfinance-mcp serve
```

Or manually add to `~/.claude.json` under your project's `mcpServers`:

```json
{
  "projects": {
    "/path/to/your/project": {
      "mcpServers": {
        "idio-yf": {
          "type": "stdio",
          "command": "make",
          "args": ["-C", "/absolute/path/to/yfinance-mcp", "serve"],
          "env": {}
        }
      }
    }
  }
}
```

**Why this approach?**
- Single source of truth (Makefile defines the server command)
- No need to remember poetry/python invocation details
- Self-documenting (Makefile is version controlled)
- Works from any directory (make -C handles working directory)

**Method 2: Direct command (alternative)**

If you prefer not to use make:

```bash
claude mcp add idio-yf poetry run python -m yfmcp.server --cwd /path/to/yfinance-mcp
```

Or manually:

```json
{
  "projects": {
    "/path/to/your/project": {
      "mcpServers": {
        "idio-yf": {
          "type": "stdio",
          "command": "poetry",
          "args": ["run", "python", "-m", "yfmcp.server"],
          "cwd": "/absolute/path/to/yfinance-mcp",
          "env": {}
        }
      }
    }
  }
}
```

**Note:** MCP servers in Claude Code are configured per-project in `~/.claude.json`, not in `~/.config/claude/mcp.json`.

### 3. Restart Claude Code

After configuration, restart Claude Code to load the MCP server.

**How it works:** Claude Code launches the MCP server as a subprocess and communicates via stdin/stdout. All processing happens locally on your machine.

## Usage

### Market Snapshot (Auto)

No parameters needed - automatically shows relevant data based on time:

```python
mcp__idio_yf__get_market_data()
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
mcp__idio_yf__get_market_data(
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
mcp__idio_yf__get_market_data(
    data_type='current',
    symbol='AAPL'
)
```

### Historical Data

Fetch price history:

```python
mcp__idio_yf__get_market_data(
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

### Quick Start

**Using Makefile (recommended):**

```bash
make all        # Run lint + test (ALWAYS before committing)
make test       # Run tests
make lint       # Run type checking + linting
make lint-fix   # Auto-fix linting issues
make serve      # Run MCP server (stdio mode)
make help       # Show all commands
```

**Manual testing (no MCP required):**

```bash
# Run tests
poetry run python tests/test_core.py

# Test core functions directly
poetry run python -c "
from yfmcp.market_data import get_market_snapshot, format_market_snapshot
data = get_market_snapshot(['futures', 'crypto'])
print(format_market_snapshot(data))
"
```

### Project Structure

```
idio-yfinance-mcp/
├── yfmcp/              # Core package (all application code)
│   ├── server.py       # MCP protocol wrapper
│   ├── market_data.py  # Core business logic (testable independently)
│   └── cli.py          # CLI tools
├── tests/              # Tests
│   └── test_core.py
├── docs/               # Documentation & exploration
├── Makefile            # Development commands
└── pyproject.toml      # Poetry config + mypy/ruff settings
```

### Documentation

- **DEVELOPER.md** - Design philosophy, engineering principles, development process
- **CLAUDE.md** - Import reference for Claude Code

### Design Principles

- **Separation of Concerns** - Business logic has zero MCP dependencies
- **Single Source of Truth** - One true path for every piece of data/logic
- **Human-Readable Output** - Format for humans, not machines
- **Keep It Simple** - Match manual testing exactly, no overengineering

## License

MIT
