# yfinance MCP Server - Developer Context

Custom Model Context Protocol server for Yahoo Finance data - built for idio project.

## Quick Start

```bash
# Development
make all        # lint + test (ALWAYS before committing)
make server     # Run MCP server (HTTP on port 5001)
make logs       # Tail server logs

# Testing
./cli list-tools           # See what Claude sees
./cli markets              # Test market overview
./cli sector technology    # Test sector drill-down
./cli ticker TSLA          # Test single ticker
./cli ticker TSLA F GM     # Test batch comparison (space-separated)
./cli options PALL         # Test options analysis
```

## Architecture

**Clean separation:**
- `yfinance_ux_mcp/market_data.py` - Business logic (zero MCP dependencies)
- `yfinance_ux_mcp/tools.py` - MCP tool definitions (single source of truth)
- `yfinance_ux_mcp/server.py` - MCP protocol wrapper, stdio transport (for local CLI)
- `yfinance_ux_mcp/server_http.py` - MCP protocol wrapper, SSE/HTTP transport (for alpha-server)
- `yfinance_ux_mcp/historical.py` - Optimized data fetching
- `yfinance_ux_mcp/cli.py` - CLI for testing

**No MCP in business logic. Protocol layer is just routing.**

**DRY principle enforced:**
- Tool definitions live in `tools.py` **only** (single source of truth)
- Both `server.py` and `server_http.py` import from `tools.py`
- To add/modify tools: Edit `tools.py` (not the server files)
- Both servers automatically get the same tool set
- Test: `./cli list-tools` and check alpha-server connections

## Tools (4 Screens)

**Hierarchical naming:** Tools use `ticker_*` prefix to show relationship:
- `ticker()` - Main security screen
- `ticker_options()` - Options tab/drill-down for a ticker

**Why this matters:** Prevents confusion (e.g., "options" could mean settings/config). Makes hierarchy explicit for UI design (tabs in alpha-server).

**Concrete examples in descriptions:** Each tool description includes actual output format so Claude sees what data is available without testing first.

### markets()
**Market overview - complete factor landscape**

No parameters. Shows:
- US EQUITIES (S&P 500, Nasdaq, Dow, Russell 2000)
- GLOBAL (Asia, Europe, Latin America)
- SECTORS (all 11 GICS sectors)
- STYLES (Momentum, Value, Growth, Quality, Size)
- COMMODITIES (Gold, Oil, Natural Gas)
- VOLATILITY & RATES (VIX, 10Y Treasury)

All with momentum (1M, 1Y trailing returns).

### sector(name)
**Sector drill-down - detailed sector analysis**

Parameters: `name` (e.g., 'technology', 'financials', 'healthcare')

Shows:
- Sector ETF price and momentum (1M, 1Y)
- Top 10 holdings with weights, prices, momentum

### ticker(symbol)
**Individual security - complete factor analysis**

Parameters: `symbol` as string or array

**Single mode** (`'TSLA'`): Full analysis with factor exposures, valuation, technicals, calendar, options summary

**Batch mode** (`['TSLA', 'F', 'GM']`): Side-by-side comparison table

Displays:
- Factor exposures (Beta SPX, Idio Vol, Total Vol)
- Valuation (P/E, Forward P/E, Dividend Yield)
- Calendar (Earnings, Ex-Div, Div Payment)
- Momentum & Technicals (1W, 1M, 1Y, 50-day MA, 200-day MA, RSI)
- 52-week range with visual bar
- Options Positioning Summary (P/C ratio, ATM IV, nearest expiration, pointer to ticker_options for full analysis)

### ticker_options(symbol, expiration='nearest')
**Options chain analysis - comprehensive positioning, IV, volume, and unusual activity**

Parameters:
- `symbol` (e.g., 'PALL', 'AAPL')
- `expiration` (optional): 'nearest' or 'YYYY-MM-DD'

Shows EVERYTHING:
- **Positioning (OI)**: P/C ratio, total OI, sentiment, ITM/OTM breakdown with percentages
- **Top Strikes by OI**: Top 10 calls/puts with OI, volume, last price, IV (side-by-side table)
- **Top Strikes by Volume**: Top 10 calls/puts with volume > OI (identifies new positions)
- **IV Structure**: ATM IV for calls/puts, spread analysis, richness indicators
- **Vol Skew**: OTM vs ATM (panic premium detection, asymmetry)
- **Term Structure**: Near/mid/far IV, contango analysis (vol compression expectations)
- **Volume Analysis**: P/C volume ratio, sentiment, comparison with OI positioning
- **Max Pain**: Strike minimizing option seller losses, current price vs max pain
- **Unusual Activity**: Flags strikes with volume > 2x OI, top examples with ratios
- **Historical IV Context**: 30-day historical volatility, 52-week IV range, IV rank percentile
- **All Expirations**: Summary table of all available expirations with IV/OI/volume
- **Interpretation**: Context insights based on data patterns (NO recommendations)

**Navigation:** Used from ticker() for detailed options analysis (ticker shows brief summary), or directly.

## Core Principles

### 1. Separation of Concerns
Business logic (market_data.py) has ZERO MCP dependencies. Protocol layer (server.py) is just routing.

### 2. Single Source of Truth
One place for each piece of data/logic. Import, don't duplicate.

### 3. UI, Not API
Tools match Bloomberg Terminal screens (markets → sector → ticker), not REST endpoints.

Each screen = one question answered:
- markets() = "What's the market doing?"
- sector('technology') = "How's this sector performing?"
- ticker('TSLA') = "Tell me about this stock?"
- ticker_options('PALL') = "What's the options positioning?" (tab/drill-down from ticker)

**Tab structure:** ticker() is the main screen, with ticker_options() as a tab/drill-down. This matches the intended alpha-server UI design (ticker page with Overview | Options tabs).

### 4. Human-Readable Output
BBG Lite formatted text (dense, scannable, professional). Not JSON. Claude reads it directly.

### 5. Strict Type Checking
Zero warnings, zero errors. Mypy strict + ruff comprehensive. Catch errors at dev time like Rust.

```bash
make all  # Must pass before committing
```

## Performance Optimizations

**fast_info instead of ticker.info** - Much faster for price/change data (markets, sector screens)

**Narrow window momentum** - Fetch ~22 days vs 252 days (91% reduction)
```python
# Current price from fast_info (no fetch)
current_price = ticker.fast_info.get("lastPrice")

# Narrow windows around exact dates (7 days, 30 days, 365 days ago)
price_1w_ago = fetch_price_at_date(symbol, date_1w_ago)
price_1m_ago = fetch_price_at_date(symbol, date_1m_ago)
price_1y_ago = fetch_price_at_date(symbol, date_1y_ago)

# Calculate momentum (precise calendar lookback)
momentum_1w = ((current_price - price_1w_ago) / price_1w_ago * 100)
```

**Parallel fetching** - ThreadPoolExecutor for concurrent API calls (markets, sector holdings)

**Batch API** - `yf.Tickers()` for multi-symbol fetches (ticker batch mode)

## Core Functions (market_data.py)

**Screen data fetchers:**
- `get_markets_data()` → Fetch all market data
- `get_sector_data(name)` → Fetch sector ETF + holdings
- `get_ticker_screen_data(symbol)` → Fetch comprehensive ticker data (includes 1W momentum and options summary)
- `get_ticker_screen_data_batch(symbols)` → Batch fetch for comparison
- `get_options_data(symbol, expiration)` → Fetch comprehensive options chain (OI, volume, ITM/OTM, max pain, unusual activity, historical IV, all expirations)

**Screen formatters (BBG Lite):**
- `format_markets(data)` → Market overview screen
- `format_sector(data)` → Sector drill-down screen
- `format_ticker(data)` → Single ticker screen (includes options positioning summary)
- `format_ticker_batch(data_list)` → Batch comparison screen
- `format_options(data)` → Comprehensive options analysis screen (OI, volume, max pain, unusual activity, historical IV, all expirations)
- `format_options_summary(data)` → Brief options summary for ticker() screen (P/C ratio, ATM IV, nearest expiration)

**Calculations:**
- `calculate_momentum(symbol)` → 1W, 1M, 1Y trailing returns (optimized narrow window fetching)
- `calculate_idio_vol(symbol)` → Idiosyncratic volatility (parallel fetch)
- `calculate_rsi(prices, period=14)` → RSI calculation
- `is_market_open()` → US market hours detection

## Testing

**CLI (no MCP required):**
```bash
./cli list-tools           # What Claude sees
./cli markets              # Test output
./cli sector technology
./cli ticker TSLA
./cli ticker TSLA F GM     # Batch mode (space-separated)
./cli options PALL
```

**MCP (after Claude Code restart):**
```python
mcp__yfinance-ux__markets()
mcp__yfinance-ux__sector(name='technology')
mcp__yfinance-ux__ticker(symbol='TSLA')
mcp__yfinance-ux__ticker(symbol=['TSLA', 'F', 'GM'])  # Batch
mcp__yfinance-ux__ticker_options(symbol='PALL')
mcp__yfinance-ux__ticker_options(symbol='PALL', expiration='2025-12-20')
```

**Unit tests:**
```bash
make test
```

## yfinance Usage Constraints

**CRITICAL: yfinance is an unofficial web scraper, not a sanctioned API.**

**Safe (what we do):**
- User-initiated queries only (human asks Claude → MCP call)
- One-off analysis ("What's TSLA trading at?")
- Manual market snapshots
- No background processes, no automation, no scheduled tasks

**Unsafe (never do this):**
- Cron jobs hitting yfinance every N minutes
- Background processes refreshing data automatically
- Any "set it and forget it" automation
- Continuous polling or bulk downloads

**Why this is safe:** Every call has a human in the loop. No automated scraping. Matches hobbyist/prototype use case.

**If we need automated monitoring:** Migrate to official APIs (Alpha Vantage, Polygon.io, IEX Cloud).

## File Structure

```
yfinance-ux-mcp/
├── yfinance_ux_mcp/          # Core package (all app code)
│   ├── server.py             # MCP protocol wrapper
│   ├── market_data.py        # Business logic (no MCP deps)
│   ├── historical.py         # Optimized data fetching
│   └── cli.py                # CLI tools
├── tests/                    # Tests
├── docs/                     # Documentation
├── cli                       # Bash wrapper
├── Makefile                  # Dev commands
├── pyproject.toml            # Poetry config + mypy/ruff
├── DEVELOPER.md              # This file
└── README.md                 # User docs
```

## Development Workflow

```bash
# Code quality (ALWAYS before committing)
make all        # lint + test (must pass)
make lint       # mypy + ruff
make test       # run tests
make lint-fix   # auto-fix issues

# Server management
make server     # Start server (HTTP port 5001)
make logs       # Tail logs
```

## Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.10"
yfinance = "^0.2.48"
mcp = "^1.1.2"
```

No extras. Keep it minimal.

## Summary

**4 screen-based tools** for systematic capital allocation:
- markets() - Complete factor landscape
- sector() - Sector drill-down
- ticker() - Individual security (single + batch comparison)
- ticker_options() - Positioning and IV analysis (tab/drill-down)

**BBG Lite output** - Dense, scannable, professional formatting

**Factor analysis** - Beta, idio vol, momentum for Paleologo framework

**Optimized** - fast_info, narrow windows, parallel fetching, batch API

**Clean architecture** - Business logic (no MCP deps) + thin protocol wrapper

**Strict quality** - Zero warnings/errors (mypy strict + ruff comprehensive)

This is infrastructure for systematic capital allocation. Keep it simple, keep it working, extend only when proven necessary.
