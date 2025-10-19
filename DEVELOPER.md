# yfinance MCP Server - Developer Context

Custom Model Context Protocol server for Yahoo Finance data - built for idio project.

## Core Engineering Principles

### Separation of Concerns

**All code belongs in the package, not scattered in root.**

- `yfmcp/` - Core package (business logic, testable independently)
  - `market_data.py` - Market data functions (no MCP dependencies)
  - `server.py` - MCP protocol wrapper (thin layer)
  - `cli.py` - CLI tools
- `tests/` - Tests (standard Python convention)
- `docs/` - Documentation and exploration scripts

**Clean boundaries:**
- Business logic has ZERO MCP dependencies
- Protocol layer is a thin wrapper
- Each module has one clear responsibility

### Single Source of Truth (One True Path)

**Every piece of data and logic should live in exactly ONE place.**

- Market symbols → `MARKET_SYMBOLS` dict in `market_data.py`
- Market hours logic → `is_market_open()` function
- Formatting logic → `format_market_snapshot()` function
- MCP protocol → `server.py` only

**No duplication.** If you need the same data or logic elsewhere, import it. Don't copy it.

### DRY (Don't Repeat Yourself)

**Corollary to Single Source of Truth.**

If you find yourself writing the same code twice:
1. Stop
2. Extract it to a function/constant
3. Import it where needed

### No Root Clutter

**Keep root directory clean.** All application code goes in `yfmcp/` package.

**What belongs in root:**
- `pyproject.toml` - Project config
- `README.md` - User docs
- `DEVELOPER.md` - This file
- `CLAUDE.md` - Import reference

**What doesn't belong in root:**
- ~~server.py~~ → `yfmcp/server.py`
- ~~cli.py~~ → `yfmcp/cli.py`
- ~~test_core.py~~ → `tests/test_core.py`

### Strict Type Checking & Linting (Rust-Style)

**Zero warnings, zero errors. Clean code means no warnings.**

We use strict type checking (mypy) and comprehensive linting (ruff) to catch errors at development time, like Rust's compiler.

**Run checks before committing:**
```bash
# ALWAYS run before committing
make all        # Run lint + test (full check)

# Individual commands
make lint       # Run mypy + ruff
make test       # Run tests
make lint-fix   # Auto-fix linting issues

# Or use poetry directly
poetry run mypy yfmcp/
poetry run ruff check yfmcp/
```

**All code must:**
- Have complete type annotations (functions, parameters, return values)
- Pass mypy strict mode (no `Any` without justification)
- Pass ruff comprehensive checks (100+ rules enabled)
- Have no warnings or errors

**Configuration** (in `pyproject.toml`):
- **mypy**: `strict = true` + additional checks (warn_unused_ignores, warn_return_any, etc.)
- **ruff**: Comprehensive rule set (Pyflakes, pycodestyle, isort, flake8-annotations, flake8-bugbear, pylint, and more)
- **Line length**: 100 characters max

**Benefits:**
- Catch errors before runtime (like Rust)
- Self-documenting code (types show intent)
- Better IDE support (autocomplete, refactoring)
- Easier onboarding (types explain interfaces)

**When to suppress:**
- External libraries without type stubs (`# type: ignore[import-untyped]`)
- MCP decorators (`# type: ignore[misc]`)
- Specific rule violations with justification (`# noqa: PLR0912` with comment explaining why)

### Development Practices

**Clean code standards - enforced by linter and type checker.**

**Imports:**
- **Always at top of file** - Never import inside functions (except when absolutely necessary for circular dependencies)
- **Sorted automatically** - ruff handles import sorting (isort)
- **One import per line** for clarity

**Before declaring work done:**
```bash
# ALWAYS run before committing
make lint    # Fix and check linting
make test    # Run all tests
```

**Code organization:**
- **One function, one responsibility** - Keep functions focused
- **Descriptive names** - `get_ticker_data()` not `get_data()`
- **Type everything** - Functions, parameters, return values, variables
- **Constants at top** - `WEEKEND_START_DAY = 5` not magic numbers in code
- **No dead code** - Delete it, don't comment it out (we have git)

**Error handling:**
- **Assign f-strings before raising** - `msg = f"Error: {x}"; raise ValueError(msg)`
- **Specific exceptions** - `ValueError` not `Exception`
- **Let it fail** - Don't catch exceptions unless you can handle them

**Performance:**

**Python is Python - it's not our biggest problem. Just don't be sloppy.**

*Core principles:*
- **Use the right data structures** - Dict for lookups (O(1)), not list (O(n))
- **Don't repeat work** - Cache lookups, use comprehensions
- **Simple > clever** - Direct code beats fancy patterns
- **Profile if it matters** - Use `cProfile` or `py-spy` when something is actually slow

*Python performance rules:*
1. **Use built-ins** - `sum()`, `max()`, `min()` are C-optimized
2. **List comprehensions** - Faster than `for` loops: `[x*2 for x in items]`
3. **Avoid repeated lookups** - Cache `obj.attr` in local variable
4. **Local variables are fast** - Don't use globals in tight loops
5. **Dict lookups O(1)** - Use dicts for fast lookups, not lists O(n)
6. **Generator expressions** - Use `(x for x in items)` for large datasets
7. **`join()` for strings** - `"".join(items)` not `s += item` in loop
8. **Avoid exceptions for flow** - Exceptions are expensive (use `if` checks)
9. **Use `set` for membership** - `x in myset` O(1) vs `x in mylist` O(n)
10. **Minimize function calls** - Function call overhead adds up in loops

*Examples:*
```python
# SLOW - repeated attribute lookup
for item in items:
    result.append(item.lower())

# FAST - cache method reference
lower = str.lower
for item in items:
    result.append(lower(item))

# EVEN FASTER - list comprehension (built-in)
result = [item.lower() for item in items]
```

```python
# SLOW - string concatenation in loop
result = ""
for s in strings:
    result += s

# FAST - join
result = "".join(strings)
```

```python
# SLOW - linear search
if symbol in symbol_list:  # O(n)
    ...

# FAST - set/dict lookup
if symbol in symbol_set:  # O(1)
    ...
```

*Profiling (find real bottlenecks):*
```bash
# Profile with cProfile (built-in)
python -m cProfile -s cumulative -m yfmcp.server

# Or use py-spy for live profiling (install: pip install py-spy)
py-spy top --pid <process_id>

# Time specific operations
import time
start = time.perf_counter()
result = expensive_function()
elapsed = time.perf_counter() - start
print(f"Took {elapsed:.4f}s")

# Benchmark with timeit (for small code snippets)
python -m timeit -s "from yfmcp.market_data import get_ticker_data" \
  "get_ticker_data('AAPL')"
```

*When to optimize:*
- **When something is actually slow** - Profile first, don't guess
- **Never prematurely** - Good code structure first, then optimize if needed

*Reality check for this codebase:*
- **Bottleneck**: yfinance API calls (network I/O)
- **Not the bottleneck**: Our Python code
- **Takeaway**: Write clean code with good data structures. Don't micro-optimize Python.

**Testing:**
- **Test business logic** - `tests/test_core.py` tests `market_data.py` independently
- **No MCP in tests** - Test core functions without protocol layer
- **All tests must pass** before declaring done

## Design Philosophy

### 1. Keep It Simple

**Don't overengineer.** The implementation matches exactly what works in manual testing - no extra complexity, no premature abstraction.

- Use the same yfinance API calls that work manually
- No fallback logic without evidence it's needed
- No extra fields until there's a use case
- Keep the code readable and maintainable

**Example:** Initial version had complex fallback logic (`currentPrice or regularMarketPrice`), manual change_percent calculation, extra fields (volume, market_cap, name). All removed because the simple approach worked.

### 2. Human-Readable Output

**Tools should output formatted data, not raw JSON.** The AI should receive information ready to interpret, not data that needs parsing.

Manual call format:
```
=== MARKETS - October 16, 2025 ===

US FUTURES:
S&P 500       6733.00 (+0.27%)
Nasdaq       25089.50 (+0.66%)
Dow          46568.00 (+0.16%)

CRYPTO:
Bitcoin      $111494.80 (+0.63%)
Ethereum     $ 4066.60 (+1.99%)
```

MCP output matches exactly - same format, same presentation, immediately useful.

**Why this matters:** The AI doesn't have to write code to parse and format the output. It just reads it and uses it directly.

### 3. UI, Not API

**Tools should match UI screens, not API endpoints.** If we wanted the API, Claude could just `import yfinance`.

**The insight from @meta/MCP_DEVELOPMENT.md:**
> "Tools for the model should be one-to-one with your UI, not your API."
> — Erik, Multi-Agent Research, Anthropic

**API thinking (wrong):**
```python
# One parameterized function that switches behavior
get_market_data(data_type='snapshot', categories=['futures'])
get_market_data(data_type='current', symbol='TSLA')
get_market_data(data_type='history', symbol='TSLA', period='3mo')
```

**UI thinking (right):**
```python
# Each tool is a screen, like navigating Bloomberg Terminal
markets()              # Market overview screen
sector('technology')   # Sector drill-down screen
ticker('TSLA')         # Individual ticker screen
```

**Navigation hierarchy:**
```
markets()              # "What's the market doing?"
   ↓ drill down
sector('technology')   # "How's this sector performing?"
   ↓ drill down
ticker('AAPL')        # "Tell me about this stock"
```

Each screen shows:
- **Factors relevant to that context** - Beta, momentum, idio vol at appropriate level
- **Navigation affordances** - Where you can go next ("Drill down: sector('technology')")
- **Complete context** - Timestamp, source, market hours status

**Why this matters:** Aligns with Paleologo workflow (systematic capital allocation):
1. **markets()** → Understand systematic risk (what is beta doing?)
2. **sector('xyz')** → Understand industry factor exposures
3. **ticker('xyz')** → Understand individual security (beta, idio vol, momentum)
4. Portfolio-level tools (separate) → Position sizing, risk decomposition, attribution

**Not parameterized API calls** - Navigation hierarchy like a human would use.

### Screen Design

**Each tool = one screen = one question answered.**

#### markets() - "What's the market doing?"

Shows market overview with factors at market level:

```
MARKETS 2025-10-19 10:48 EDT | Market hours

US EQUITIES
S&P 500      6733.00   +0.27%   β 1.00   +1.2% (1M)   +24.8% (1Y)
Nasdaq      25089.50   +0.66%   β 1.15   +2.1% (1M)   +28.4% (1Y)
Dow         46568.00   +0.16%   β 0.92   +0.8% (1M)   +18.2% (1Y)

SECTORS
Technology       285.01   +0.18%   β 1.28   +3.4% (1M)   +24.2% (1Y)
Financials       143.27   +0.67%   β 1.12   +4.7% (1M)    -4.8% (1Y)
Healthcare       167.89   +0.23%   β 0.88   +2.1% (1M)   +12.3% (1Y)
[all 11 GICS sectors]

STYLES
Momentum         252.80   -0.04%   β 1.05   -0.7% (1M)   +22.0% (1Y)
Value            185.64   +0.50%   β 0.95   +0.4% (1M)    +6.7% (1Y)
Growth           478.24   +0.45%   β 1.02   +0.6% (1M)   +22.5% (1Y)

COMMODITIES
Gold            2742.30   β 0.12   +5.2% (1M)   +15.8% (1Y)
Oil (WTI)         71.24   β 0.25  -12.4% (1M)    -8.2% (1Y)

VOLATILITY & RATES
VIX               16.42   -15.2% (1M)   -22.3% (1Y)
10Y Treasury      4.23%    +0.8% (1M)    +2.4% (1Y)

Data as of 2025-10-19 10:48 EDT | Source: yfinance
Drill down: sector('technology') | ticker('AAPL')
```

**Factors shown:** Beta (vs SPX), momentum (1M, 1Y) - always, no parameters

#### sector('technology') - "How's this sector performing?"

Shows sector-level factors and top constituents:

```
TECHNOLOGY SECTOR                         XLK 285.01 +0.18%

SECTOR FACTORS
Beta to SPX      1.28    (High sensitivity)
Momentum 1M      +3.4%
Momentum 1Y     +24.2%
Idio Vol        14.2%

TOP HOLDINGS
AAPL    242.50   +2.43%   β 1.15   23.4% weight
MSFT    415.20   +1.85%   β 1.22   21.2% weight
NVDA    892.45   +3.12%   β 1.85   15.8% weight
[top 10 holdings]

Data as of 2025-10-19 10:48 EDT | Source: yfinance
Back: markets() | Drill down: ticker('AAPL')
```

**Factors shown:** Sector beta, momentum, idio vol, constituent betas

#### ticker('TSLA') - "Tell me about this stock"

Shows individual security with complete factor exposures:

```
TSLA US EQUITY                   LAST PRICE  242.50 +5.75  +2.43%
TESLA INC                        MKT CAP     770.5B    VOLUME 15.2M

FACTOR EXPOSURES
Beta (SPX)       2.08    (High sensitivity)
Sector           Technology (XLK)
Beta (XLK)       1.62    (vs sector)
Idio Vol         32.4%   (High stock-specific risk)

MOMENTUM
1-Month          +8.4%
1-Year          +48.2%
RSI (14D)        72.3    (Overbought)

52-WEEK RANGE
High             299.29
Low              138.80
Current          242.50  [===════════░░░░░░░]  67% of range

Data as of 2025-10-19 10:48 EDT | Source: yfinance
Back: sector('technology') | Compare: ticker('F')
```

**Factors shown:** Beta (SPX and sector), idio vol, momentum, RSI, range

**Key design principle:** Each screen shows factors relevant to that level. Market screen shows market-level betas. Ticker screen shows individual security factors. Navigation affordances show where you can go.

### Implementation Plan: API → UI Redesign

**Current state:** One parameterized tool `get_market_data(data_type, categories, symbol, period, show_momentum)`

**Target state:** Three screen-based tools

#### Tool 1: markets()

**Purpose:** "What's the market doing?"

**No parameters** - shows complete market overview with all factors

**Data displayed:**
- US EQUITIES: S&P 500, Nasdaq, Dow, Russell 2000 (with β, momentum 1M/1Y)
- GLOBAL: Europe (STOXX 50), Asia (Nikkei), China (Shanghai)
- SECTORS: All 11 GICS sectors (XLK, XLF, XLV, etc.) with β, momentum
- STYLES: Momentum (MTUM), Value (VTV), Growth (VUG), Quality (QUAL), Size (IWM)
- COMMODITIES: Gold, Oil, Natural Gas (with β, momentum)
- VOLATILITY & RATES: VIX, 10Y Treasury (momentum only)

**From yfinance:**
```python
# For each symbol
price = ticker.info.get('regularMarketPrice') or ticker.info.get('currentPrice')
change_pct = ticker.info.get('regularMarketChangePercent')
beta = ticker.info.get('beta')
# Calculate momentum from ticker.history(period='1y')
```

**Footer:** Navigation affordances ("Drill down: sector('technology') | ticker('AAPL')")

#### Tool 2: sector(name)

**Purpose:** "How's this sector performing?"

**Parameters:**
- `name` (required): Sector name - enum: ['technology', 'financials', 'healthcare', 'energy', 'consumer_disc', 'consumer_stpl', 'industrials', 'utilities', 'materials', 'real_estate', 'communication']

**Data displayed:**
- Sector ETF price/change (XLK for technology)
- Sector factors: Beta to SPX, Momentum (1M, 1Y), Idio Vol
- Top holdings: Top 10 constituents with price, change, beta, weight

**From yfinance:**
```python
# Sector ETF
sector_etf = yf.Ticker('XLK')
beta = sector_etf.info.get('beta')
# Calculate idio vol from history

# Holdings
holdings = sector_etf.info.get('holdings')  # Top holdings with weights
# Fetch each holding's data
```

**Footer:** Navigation ("Back: markets() | Drill down: ticker('AAPL')")

#### Tool 3: ticker(symbol)

**Purpose:** "Tell me about this stock"

**Parameters:**
- `symbol` (required): Ticker symbol (e.g., 'TSLA', 'AAPL')

**Data displayed:**

**Header:**
- Price, change, market cap, volume

**Factor Exposures:**
- Beta (SPX) - `ticker.info['beta']`
- Beta (sector) - Calculate vs sector ETF
- Idio Vol (ann) - Calculate from historical returns minus market/sector
- Total Vol (ann) - Calculate from historical returns

**Valuation:**
- P/E Ratio - `ticker.info['trailingPE']`
- Forward P/E - `ticker.info['forwardPE']`
- Dividend Yield - `ticker.info['dividendYield']`

**Momentum & Technicals:**
- 1-Month, 1-Year, YTD - Calculate from `.history()`
- 50-Day MA - `ticker.info['fiftyDayAverage']`
- 200-Day MA - `ticker.info['twoHundredDayAverage']`
- RSI (14D) - Calculate from `.history(period='1mo')`

**52-Week Range:**
- High - `ticker.info['fiftyTwoWeekHigh']`
- Low - `ticker.info['fiftyTwoWeekLow']`
- Visual bar showing current position in range

**Footer:** Navigation ("Back: sector('technology') | Compare: ticker('F')")

#### Implementation Steps

1. **Update server.py** - Replace single tool with three:
   - `markets` (no params)
   - `sector` (name param with enum)
   - `ticker` (symbol param)

2. **Update market_data.py** - New functions:
   - `get_markets_data()` - Fetch all market overview data
   - `format_markets()` - BBG Lite formatting for market screen
   - `get_sector_data(name)` - Fetch sector ETF + holdings
   - `format_sector(data)` - BBG Lite formatting for sector screen
   - `get_ticker_data(symbol)` - Fetch all ticker metrics
   - `format_ticker(data)` - BBG Lite formatting for ticker screen
   - `calculate_idio_vol(symbol)` - Idio volatility calculation
   - `calculate_rsi(prices, period=14)` - RSI calculation

3. **Update cli.py** - New commands:
   - `./cli markets`
   - `./cli sector technology`
   - `./cli ticker TSLA`

4. **Test with CLI** - Verify outputs match BBG Lite design before MCP integration

5. **Update tests** - New test cases for each screen

6. **Update README.md** - New usage examples

#### Data Requirements

**New calculations needed:**

**Idiosyncratic volatility:**
```python
# 1-year daily returns
ticker_returns = ticker.history(period='1y')['Close'].pct_change()
market_returns = yf.Ticker('^GSPC').history(period='1y')['Close'].pct_change()

# Regression to get beta and alpha
beta, alpha = np.polyfit(market_returns, ticker_returns, 1)

# Residuals = idiosyncratic component
residuals = ticker_returns - (alpha + beta * market_returns)
idio_vol = residuals.std() * np.sqrt(252)  # Annualized
```

**RSI (14-day):**
```python
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]
```

**Momentum (1M, 1Y):**
```python
hist = ticker.history(period='1y')
current = hist['Close'].iloc[-1]
one_month_ago = hist['Close'].iloc[-21]  # ~21 trading days
one_year_ago = hist['Close'].iloc[0]

momentum_1m = ((current - one_month_ago) / one_month_ago) * 100
momentum_1y = ((current - one_year_ago) / one_year_ago) * 100
```

#### Execution Strategy

**No migration. No deprecation. Replace everything.**

**Single Source of Truth:** One right way to do things. Delete old code, write new code, test, ship.

1. Delete old `get_market_data` implementation from server.py
2. Delete old market_data.py functions (or refactor into new screens)
3. Implement new three-tool design
4. Test with CLI
5. Update README
6. Done

**This is a complete rewrite, not a migration.** The old API-style tool was wrong. The new UI-style tools are right. No backward compatibility needed - we're the only user.

### 4. PMF Testing Methodology

**Build → Use → Iterate.** Test with real usage from day one.

The actual development process:

1. User asks: "What do markets look like?"
2. I write manual Python script using yfinance
3. Verify output format is useful
4. User says "now build MCP with that"
5. I overengineer the MCP (extra fields, fallback logic)
6. User says "why isn't it the same as manual?"
7. I simplify to match manual code exactly
8. User says "format isn't right"
9. I fix format to match manual output
10. Done - now it works

**Key insight:** Steps 5-9 could have been skipped by just wrapping the manual code in MCP from the start.

Don't build features speculatively. Build what's needed now, based on real usage.

## Development Process

### Initial Manual Script

Started with direct yfinance testing:

```python
import yfinance as yf

print('=== MARKETS - October 16, 2025 ===\n')

print('US FUTURES:')
for name, symbol in [('S&P 500', 'ES=F'), ('Nasdaq', 'NQ=F'), ('Dow', 'YM=F')]:
    ticker = yf.Ticker(symbol)
    info = ticker.info
    price = info.get('regularMarketPrice') or info.get('currentPrice')
    change_pct = info.get('regularMarketChangePercent')
    if price and change_pct:
        print(f'{name:12} {price:8.2f} ({change_pct:+.2f}%)')
```

This worked. So we used this exact pattern in the MCP.

### What We Changed (and Why)

**Added:**
- Market hours detection (is_market_open)
- Auto-detect categories based on market hours
- Smart defaults (no params needed)

**Reason:** Real usage pattern - check markets in the morning (want futures), check during day (want indices).

**Didn't Add:**
- Caching
- Rate limiting
- Error recovery
- Retry logic
- Additional data fields
- Complex fallback chains

**Reason:** No evidence these are needed yet. Add when proven necessary.

## Smart Defaults

### Market Hours Auto-Detection

```python
def is_market_open() -> bool:
    """Check if US market is currently open (9:30 AM - 4:00 PM ET, Mon-Fri)"""
    now_et = datetime.now(ZoneInfo("America/New_York"))

    if now_et.weekday() >= 5:  # Weekend
        return False

    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now_et < market_close
```

When no categories specified:

**Market open** (9:30 AM - 4:00 PM ET, Mon-Fri):
- Shows US INDICES (cash market: S&P 500, Nasdaq, Dow)
- Plus crypto and commodities

**After hours:**
- Shows US FUTURES (ES, NQ, YM)
- Plus crypto and commodities

This matches actual usage - you check futures before market open, indices during market hours.

## Development Lessons

### What We Learned

1. **Test with real usage first** - Built the manual Python script, verified it works, then wrapped it in MCP
2. **Match the working code exactly** - No "improvements" without evidence
3. **Format for humans, not machines** - Tools should output ready-to-use information
4. **Simple beats clever** - Direct API calls beat elaborate fallback logic
5. **PMF testing works** - Building for immediate use reveals what's actually needed

### What We Avoided

**Premature optimization:**
- ❌ Caching (not needed - yfinance is fast enough)
- ❌ Rate limiting (not hitting limits)
- ❌ Error recovery (errors are rare, fail fast is fine)

**Over-abstraction:**
- ❌ Complex type hierarchies
- ❌ Excessive parameters
- ❌ Configuration files
- ❌ Plugin systems

**Machine-first output:**
- ❌ Raw JSON that needs interpretation
- ❌ Structured data requiring parsing
- ❌ Nested objects requiring traversal

**Feature speculation:**
- ❌ "We might need this later"
- ❌ "This would be cool to have"
- ❌ "Let me add some flexibility"

### Mistakes Made (and Fixed)

**Mistake 1: Overengineering get_ticker_data**

```python
# Initial (wrong)
current_price = info.get('currentPrice') or info.get('regularMarketPrice')
prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose')

if current_price and prev_close:
    change = current_price - prev_close
    change_pct = (change / prev_close) * 100
else:
    change = None
    change_pct = None

return {
    "symbol": symbol,
    "price": current_price,
    "previous_close": prev_close,
    "change": change,
    "change_percent": change_pct,
    "volume": info.get('volume'),
    "market_cap": info.get('marketCap'),
    "name": info.get('longName') or info.get('shortName'),
}
```

**Fixed (simple):**
```python
price = info.get('regularMarketPrice') or info.get('currentPrice')
change_pct = info.get('regularMarketChangePercent')

return {
    "symbol": symbol,
    "price": price,
    "change_percent": change_pct,
}
```

**Lesson:** Match the manual code exactly. No extra fields, no manual calculations, no fallback chains without evidence.

**Mistake 2: Wrong output format**

First version had `$` on all prices. Manual code had `$` only on crypto and commodities.

**Lesson:** Format must match manual code exactly. Test the output, not just the logic.

**Mistake 3: Including raw JSON in output**

Initial snapshot returned:
```
Market Snapshot:

sp500: $6692.26 (+0.32%)
...

Raw data:
{ "sp500": { "symbol": "^GSPC", "price": 6692.26, ... } }
```

**Fixed:** Return only formatted output.

**Lesson:** Human-readable output means human-readable only. No raw data dumped alongside.

## Code Structure

### Core Functions (yfmcp/market_data.py)

**`is_market_open()`** - Detects US market hours (9:30 AM - 4:00 PM ET, Mon-Fri)

**`get_ticker_data(symbol)`** - Fetches price and change_percent for single ticker
- Uses yfinance directly
- No calculations, just passes through API data
- Minimal fields (symbol, price, change_percent)

**`get_market_snapshot(categories)`** - Fetches multiple tickers by category
- Auto-detects market hours if no categories specified
- Returns dict of ticker data

**`format_market_snapshot(data)`** - Formats ticker data for human reading
- Matches manual script format exactly
- Sections by category (US FUTURES, CRYPTO, etc.)
- Friendly names (S&P 500 instead of es_futures)
- Proper formatting ($, %, alignment)

### MCP Integration (yfmcp/server.py)

**`list_tools()`** - Defines single tool: `get_market_data`

**`call_tool()`** - Handles three data_types:
- `snapshot` - Market overview (auto-detects or custom categories)
- `current` - Single ticker current price
- `history` - Historical price data

**Thin wrapper** - Imports from `market_data.py`, handles MCP protocol only

## Testing Approach

### Manual Testing First

```bash
cd /path/to/yfinance-mcp
poetry run python -c "
from yfmcp.market_data import get_market_snapshot, format_market_snapshot

data = get_market_snapshot(['futures', 'crypto', 'commodities'])
print(format_market_snapshot(data))
"
```

This must output exactly what you want before wrapping in MCP.

**Note:** Core functions in `yfmcp/market_data.py` are testable independently (no MCP required).

### CLI Testing (No MCP Required)

Test the MCP server locally without Claude Code using the CLI tool:

```bash
# List available tools (what Claude sees)
./cli list-tools

# Call a tool (what Claude receives)
./cli call get_market_data --data_type snapshot --categories futures,crypto
./cli call get_market_data --data_type current --symbol AAPL
./cli call get_market_data --data_type history --symbol TSLA --period 3mo
```

**Zero drift:** CLI uses the actual MCP server handlers, so output matches exactly what Claude receives.

### Unit Testing

Run the test suite:

```bash
poetry run python tests/test_core.py
```

Tests verify:
- Market hours detection
- Single ticker fetch
- Market snapshot
- Output formatting

### MCP Testing

After Claude Code restart:
```python
mcp__yfinance__get_market_data(
    data_type='snapshot',
    categories=['futures', 'crypto', 'commodities']
)
```

Output should match manual test exactly.

## When to Extend

Add features only when:

1. **Real usage reveals the need** - Not speculation
2. **Manual script proven to work** - Test outside MCP first
3. **Format matches manual** - No divergence between manual and MCP
4. **Simple implementation** - No premature optimization

**Example of good addition:**
- User checks markets every morning at 6 AM
- Always wants futures + crypto + commodities
- Manual: writes same categories every time
- Solution: Add auto-detect based on market hours
- Result: No params needed, still works for custom categories

**Example of bad addition:**
- "We might want to cache results"
- No evidence caching is needed
- No performance problem observed
- Don't add it

## Security and Best Practices

**🚨 NEVER HARDCODE VALUES**
- No hardcoded paths, usernames, URLs, or configuration in code/docs
- Use environment variables for sensitive data
- Keep examples generic (use `/path/to/project`, not actual system paths)
- Documentation should work for any user, not just the original developer

**🚨 NEVER COMMIT SECRETS**
- No API keys, tokens, or credentials in code
- Use environment variables: `os.environ.get('API_KEY', '')`
- Add `.env` files to `.gitignore`

**Keep it simple:**
- No premature optimization
- No features without proven need
- Match manual testing exactly

## File Structure

```
yfinance-mcp/
├── yfmcp/              # Core package (all application code)
│   ├── __init__.py
│   ├── server.py       # MCP protocol wrapper
│   ├── market_data.py  # Core business logic
│   └── cli.py          # CLI tools
├── tests/              # Tests (testable independently)
│   └── test_core.py
├── docs/               # Documentation & exploration
│   └── explore_yfinance.py
├── tasks/              # Task tracking
├── cli                 # Bash wrapper for CLI
├── Makefile            # Development commands (make test, make lint, make all)
├── pyproject.toml      # Poetry dependencies + mypy/ruff config
├── DEVELOPER.md        # This file - developer context
├── CLAUDE.md           # Import reference for Claude Code
└── README.md           # User documentation
```

**Key principle:** All application code lives in `yfmcp/` package. Root is clean (only config, docs, and CLI wrapper).

**Development workflow:**
```bash
make all    # Run lint + test (ALWAYS before committing)
make test   # Run tests only
make lint   # Run type checking + linting
make serve  # Run MCP server (stdio mode)
```

## Dependencies

Managed with Poetry (package-mode = false):

```toml
[tool.poetry.dependencies]
python = "^3.10"
yfinance = "^0.2.48"
mcp = "^1.1.2"
```

No extras. No optional dependencies. Keep it minimal.

## Summary

**Engineering Principles:**
- **Separation of Concerns** - Business logic (zero MCP deps) + thin protocol wrapper
- **Single Source of Truth** - One true path for every piece of data/logic
- **No Root Clutter** - All application code in `yfmcp/` package
- **DRY** - Don't repeat yourself, import instead
- **Strict Checking** - Zero warnings/errors (mypy strict + ruff comprehensive)
- **High Standards** - Don't be sloppy (use right data structures, clean code, no premature optimization)

**Design Philosophy:**
- **Keep It Simple** - Build the simplest thing that solves the real problem
- **Test Manually First** - Prove it works before wrapping in MCP
- **Human-Readable Output** - Format for humans, not machines
- **Single Flexible Tool** - One tool that adapts beats many narrow tools

**PMF Testing:** Build → Use → Iterate. Real usage reveals what's needed. Speculation adds complexity without value.

This is infrastructure for investment analysis. Keep it simple, keep it working, extend only when proven necessary.
