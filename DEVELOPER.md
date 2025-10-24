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

- Market symbols → `MARKET_SYMBOLS` and `SECTOR_ETFS` dicts in `market_data.py`
- Market hours logic → `is_market_open()` function
- Formatting logic → `format_markets()`, `format_sector()`, `format_ticker()` functions
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

### Current Implementation: UI-Based Screens

**Implementation Status:**
- ✅ **markets()** - Complete and deployed
- ✅ **sector(name)** - Complete and deployed
- ❌ **ticker(symbol)** - TODO (get_ticker_data exists, needs format_ticker and MCP wiring)

**Redesign completed Oct 2025** - Migrated from parameterized API-style `get_market_data()` to Bloomberg-Terminal-style navigation screens.

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

#### Implementation Status

**✅ Completed:**

1. **server.py** - Two of three tools implemented:
   - ✅ `markets` (no params)
   - ✅ `sector` (name param)
   - ❌ `ticker` (symbol param) - TODO

2. **market_data.py** - Core functions:
   - ✅ `get_markets_data()` - Fetch all market overview data
   - ✅ `format_markets()` - BBG Lite formatting for market screen
   - ✅ `get_sector_data(name)` - Fetch sector ETF + holdings
   - ✅ `format_sector(data)` - BBG Lite formatting for sector screen
   - ✅ `get_ticker_data(symbol)` - Fetch ticker metrics (basic version exists)
   - ❌ `format_ticker(data)` - TODO: BBG Lite formatting for ticker screen
   - ❌ `calculate_idio_vol(symbol)` - TODO: Idio volatility calculation
   - ❌ `calculate_rsi(prices, period=14)` - TODO: RSI calculation

3. **cli.py** - Commands:
   - ✅ `./cli markets`
   - ✅ `./cli sector technology`
   - ✅ `./cli ticker TSLA` (basic version, uses get_ticker_data directly)

**❌ Remaining Work for ticker() screen:**

1. Implement `format_ticker(data)` in market_data.py with BBG Lite formatting
2. Implement `calculate_idio_vol(symbol)` helper
3. Implement `calculate_rsi(prices, period=14)` helper
4. Wire ticker() to server.py's list_tools() and call_tool()
5. Update tests for ticker screen
6. Update README.md with ticker() examples

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
# OPTIMIZED: fast_info for current + narrow windows for precise lookback
# Fetches ~15 days total vs 252 days (94% reduction!)
ticker = yf.Ticker(symbol)

# Current price from fast_info (no history fetch!)
current_price = ticker.fast_info.get("lastPrice")

# Calculate precise lookback dates (calendar days)
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

now = datetime.now(ZoneInfo("America/New_York"))
date_1y_ago = now - timedelta(days=365)  # Exact 1 year
date_1m_ago = now - timedelta(days=30)   # Exact 1 month

# Fetch narrow windows (~7-8 days each) around target dates
# Returns closest price to target date within window
price_1y_ago = fetch_price_at_date(symbol, date_1y_ago)
price_1m_ago = fetch_price_at_date(symbol, date_1m_ago)

# Calculate momentum
momentum_1y = ((current_price - price_1y_ago) / price_1y_ago * 100)
momentum_1m = ((current_price - price_1m_ago) / price_1m_ago * 100)
```

#### Migration Notes (Oct 2025)

**Redesign executed:** Old parameterized `get_market_data()` API-style tool replaced with three Bloomberg-Terminal-style screen tools.

**Philosophy:** No migration, no deprecation. Single source of truth - one right way to do things. We're the only user, so no backward compatibility needed.

**Result:** markets() and sector() fully functional. ticker() remains to be completed.

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

## Usage Constraints & Rate Limiting

**CRITICAL: yfinance is an unofficial web scraper, not a sanctioned API.**

### What yfinance Actually Is

- **Unofficial scraper** - Mimics browser requests to Yahoo Finance
- **No official API** - No documentation, no guarantees, no support
- **No rate limits published** - Because it's not meant to be used this way
- **Prone to blocks** - Yahoo's anti-scraping measures can trigger on suspicious patterns

### What Triggers Blocks

**Common causes of 429 errors and IP bans:**
- Frequent requests from same IP
- Patterns resembling DDoS (bulk downloads, continuous polling)
- High-volume requests
- Yahoo site changes (can break library entirely)

**Historical context:** Yahoo tightened restrictions significantly around early 2024. The library breaks periodically when Yahoo changes their site.

### Safe Usage Pattern (What We Do)

**✅ SAFE - Our current implementation:**
- **User-initiated queries only** - Human asks Claude → MCP call triggered
- **One-off analysis** - "What's TSLA trading at?" → single call
- **Manual market snapshots** - When user wants to check markets
- **Ad-hoc research** - Historical data for specific thesis work
- **No background processes** - All queries go through Claude Code
- **No scheduled tasks** - No cron jobs, no automation

**Why this is safe:** Every call has a human in the loop. No automated polling. Matches hobbyist/prototype/infrequent use case that doesn't trigger blocks.

### Unsafe Usage Pattern (What NOT to Do)

**❌ NEVER DO THIS:**
- Cron jobs hitting yfinance every N minutes
- Background processes refreshing market data automatically
- Automated monitoring loops
- Scheduled portfolio updates
- Any "set it and forget it" automation
- Continuous polling or bulk downloads

**Why this is unsafe:** Patterns resembling automated scraping trigger Yahoo's anti-DDoS measures. 429 errors, IP bans, complete blocks.

### Implications for Capital Allocation System

**yfinance is appropriate for:**
- Research and thesis development
- Ad-hoc position analysis
- One-off market checks
- Manual portfolio reviews

**yfinance is NOT appropriate for:**
- Real-time portfolio monitoring
- Live P&L tracking
- Automated alerts
- Continuous position monitoring
- Production infrastructure

**Future scaling:** If we need automated monitoring or real-time data, we'll migrate to an official API (Alpha Vantage, Polygon.io, IEX Cloud, etc.). yfinance is for PMF testing and research only.

### Bottom Line

**This MCP server is a research tool, not production infrastructure.**

All queries are human-initiated through Claude Code. No automation. No polling. This keeps us well within safe usage patterns and avoids triggering Yahoo's anti-scraping measures.

If yfinance breaks (Yahoo changes site) or gets blocked (unlikely with our usage pattern), we'll know it's time to migrate to official APIs.

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
6. **Validate optimizations with real data** - "Fast" APIs may measure different things (YTD vs 1Y). Always verify precision matches requirements before declaring optimization complete

### What We Avoided

**Premature optimization:**
- ❌ Caching (not needed - yfinance is fast enough)
- ❌ Rate limiting (not hitting limits)
- ❌ Error recovery (errors are rare, fail fast is fine)

**When we DID optimize:**
- ✅ Reducing API calls to Yahoo Finance (94% reduction) - Evidence-based: being nice to unofficial API
- ✅ Parallel fetching for factor analysis - Clear benefit: 2x faster idio vol calculations
- ✅ **BUT**: Only after validating precision with real data (caught YTD vs 1Y issue)

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

**Mistake 4: Optimizing without validating precision**

Initial momentum optimization used `fast_info['yearChange']` for 1Y momentum:
```python
# Seemed optimal (no history fetch!)
year_change = ticker.fast_info.get("yearChange")
momentum_1y = float(year_change) * 100  # But this is YTD, not 1Y!
```

**Problem discovered:** `yearChange` is **YTD** (year-to-date from Jan 1), not trailing 1-year. For TSLA: YTD was +107%, but true 1Y was +105% (1.7% difference). Significant for investment decisions.

**Fixed:** Narrow window approach - fetch 10-day windows around exact dates (365 days ago, 30 days ago):
```python
# Current price from fast_info (no fetch!)
current_price = ticker.fast_info.get("lastPrice")

# Precise lookback: narrow windows (~7-8 days each)
price_1y_ago = fetch_price_at_date(symbol, now - timedelta(days=365))
price_1m_ago = fetch_price_at_date(symbol, now - timedelta(days=30))

# Total: ~15 days fetched vs 252 days (94% reduction, still precise!)
```

**Lesson:** Test assumptions. "Fast" doesn't matter if it's measuring the wrong thing. Validate precision with real data before declaring victory. The narrow window approach gives both speed (94% reduction) AND precision (exact calendar lookback).

## Code Structure

### Historical Data Module (yfmcp/historical.py)

**Optimized historical data fetching - minimal API calls, parallel execution where possible**

**`calculate_date_range(months)`** - DRY date range calculation
- Converts months → calendar days with minimal buffer
- Returns (start_date, end_date) as ISO strings

**`fetch_price_history(symbol, months, interval)`** - Fetch minimal historical data
- Uses start/end dates instead of period (more explicit)
- Returns DataFrame with OHLCV data

**`fetch_multiple_histories(symbols, months, interval, max_workers)`** - **Parallel fetching**
- Fetches multiple symbols concurrently (ThreadPoolExecutor)
- Returns dict mapping symbol → DataFrame
- Default max_workers=10

**`fetch_ticker_and_market(symbol, months, market_symbol)`** - **Parallel factor data fetch**
- Fetches ticker + market (S&P 500) data in parallel
- Used by `calculate_idio_vol()` for regression analysis
- Returns tuple (ticker_hist, market_hist)

**`fetch_price_at_date(symbol, target_date, window_days=5)`** - **Narrow window price lookup**
- Fetches 10-day window around target date (~7-8 days actual data)
- Finds closest price to target date within window (precise lookback)
- Used by `calculate_momentum()` for 1M/1Y lookback prices
- **Key optimization:** ~15 days total vs 252 days (94% reduction)

### Core Functions (yfmcp/market_data.py)

**Performance optimization (Oct 2025):**

We discovered `ticker.info` is SLOW (full data fetch). Use `fast_info` whenever possible:

```python
# SLOW - fetches comprehensive info object
ticker = yf.Ticker(symbol)
info = ticker.info  # Full API call
price = info.get("regularMarketPrice")
change_pct = info.get("regularMarketChangePercent")

# FAST - uses lightweight fast_info
ticker = yf.Ticker(symbol)
price = ticker.fast_info.get("lastPrice")  # Much faster!
prev_close = ticker.fast_info.get("previousClose")
change_pct = ((price - prev_close) / prev_close) * 100  # Calculate locally
```

**When to use fast_info:**
- ✅ **Price + change data only** (markets screen, sector holdings) - use fast_info
- ❌ **Comprehensive data needed** (ticker screen: beta, PE ratios, dividend yield, moving averages) - use ticker.info

**Impact:**
- markets() screen: 45+ symbols, 7.2 seconds (fast_info + narrow windows + parallel)
- sector() holdings: 10 symbols, 4.2 seconds (fast_info + narrow windows + parallel)
- ticker() screen: 1 symbol, ~2-3 seconds (ticker.info justified - needs comprehensive data)

**Screen-based functions (UI navigation model):**

**`get_markets_data()`** - Fetch complete market overview data
- US equities, global indices, sectors, styles, commodities, volatility/rates
- Returns dict of all ticker data with momentum calculations

**`format_markets(data)`** - BBG Lite formatting for market screen
- Dense, scannable professional output
- Navigation affordances for drill-down

**`get_sector_data(name)`** - Fetch sector ETF + top holdings
- Sector ETF price, momentum (1M, 1Y)
- Top 10 holdings with weights
- Returns structured dict

**`format_sector(data)`** - BBG Lite formatting for sector screen
- Sector overview + constituent breakdown
- Navigation affordances

**`get_ticker_data(symbol)`** - Fetch individual ticker metrics
- Complete ticker screen: price, valuation, momentum, technicals, calendar
- Uses optimized momentum calculation (fast_info + minimal history)

**`format_ticker(data)`** - BBG Lite formatting for ticker screen
- Factor exposures, valuation, momentum, RSI, 52-week range
- Navigation affordances

**Helper functions:**

**`is_market_open()`** - Detects US market hours (9:30 AM - 4:00 PM ET, Mon-Fri)

**`calculate_momentum()`** - **OPTIMIZED:** Calculate 1M, 1Y trailing returns
- Current price: Uses `fast_info['lastPrice']` (no history fetch!)
- Lookback prices: Narrow 10-day windows around exact dates (365 days, 30 days)
- Fetches ~15 days total vs 252 days (**94% reduction**)
- Finds closest price to target date within window (precise calendar lookback)
- **Much faster and more Yahoo-friendly** than full year fetch

**`calculate_idio_vol()`** - Idiosyncratic volatility calculation
- **OPTIMIZED:** Uses parallel fetching via `fetch_ticker_and_market()`
- Regression analysis: ticker returns vs market returns
- Returns idio vol (stock-specific risk) and total vol
- **~2x faster** due to parallel execution

**`calculate_rsi(prices, period=14)`** - RSI (14-day) calculation
- Relative Strength Index from price series
- Returns single RSI value or None

### MCP Integration (yfmcp/server.py)

**`list_tools()`** - Defines screen-based tools:
- `markets` - Market overview (no params)
- `sector` - Sector drill-down (name param)
- `ticker` - Individual security (symbol param) - TODO

**`call_tool()`** - Routes to appropriate screen handler:
- `markets` → `get_markets_data()` + `format_markets()`
- `sector` → `get_sector_data(name)` + `format_sector()`
- `ticker` → TODO

**Thin wrapper** - Imports from `market_data.py`, handles MCP protocol only

## Testing Approach

### Manual Testing First

```bash
cd /path/to/yfinance-mcp
poetry run python -c "
from yfmcp.market_data import get_markets_data, format_markets

data = get_markets_data()
print(format_markets(data))
"
```

This must output exactly what you want before wrapping in MCP.

**Note:** Core functions in `yfmcp/market_data.py` are testable independently (no MCP required).

### CLI Testing (No MCP Required)

Test the MCP server locally without Claude Code using the CLI tool:

```bash
# List available tools (what Claude sees)
./cli list-tools

# Call the screen-based tools (what Claude receives)
./cli markets
./cli sector technology
./cli ticker TSLA  # TODO: Not yet wired to MCP server
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
# Market overview
mcp__idio-yf__markets()

# Sector drill-down
mcp__idio-yf__sector(name='technology')

# Individual ticker (TODO - not yet implemented)
# mcp__idio-yf__ticker(symbol='TSLA')
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
│   ├── historical.py   # Optimized historical data fetching (parallel, minimal API calls)
│   └── cli.py          # CLI tools
├── tests/              # Tests (testable independently)
│   └── test_core.py
├── docs/               # Documentation & exploration
│   ├── explore_yfinance.py
│   └── YFINANCE_CAPABILITIES.md  # yfinance API reference
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
make stdio  # Run MCP server (stdio mode for Claude Code)
make server # Run MCP HTTP server (port 5001, kills existing, uses nohup)
make logs   # Tail server logs
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
