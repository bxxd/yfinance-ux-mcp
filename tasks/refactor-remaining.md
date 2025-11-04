# Refactor Remaining Work

**Status**: Phase 1 complete (constants extracted)
**Branch**: `refactor/separate-concerns`
**Progress**: 1 of 6 phases complete

---

## ✅ Phase 1: Constants (COMPLETE)

**What was done:**
- Created directory structure: `common/`, `calculations/`, `services/`, `formatters/`
- Extracted 248 lines of constants to `common/constants.py`
- Removed 180 lines from `market_data.py` (2,221 → 2,045 lines)
- All tests passing, no regressions

**Files:**
- `common/constants.py` - All mappings, thresholds, display names, symbols

---

## 🚧 Phase 2: Common Utilities (TODO)

### 2.1 Extract `common/dates.py`

**Functions to extract:**
- `is_market_open()` - US market hours check
- `is_us_market_open()` - Duplicate of above? (check if needed)
- `is_europe_market_open()` - European market hours
- `is_asia_market_open()` - Asian market hours
- `is_futures_open()` - Futures market hours
- `get_market_status(region)` - Market status by region

**Current location:** Lines ~80-120 of `market_data.py`

**Estimated size:** ~100 lines

**Steps:**
1. Create `common/dates.py`
2. Copy functions with docstrings
3. Import constants from `common.constants`
4. Update `market_data.py` to import from `common.dates`
5. Run tests

### 2.2 Extract `common/symbols.py`

**Functions to extract:**
- `normalize_ticker_symbol(symbol)` - Exchange suffix vs share class logic

**Current location:** Lines ~40-78 of `market_data.py`

**Estimated size:** ~40 lines

**Steps:**
1. Create `common/symbols.py`
2. Move `normalize_ticker_symbol()` function
3. Update `market_data.py` to import from `common.symbols`
4. Run tests

---

## 🚧 Phase 3: Calculations (TODO)

### Extract `calculations/momentum.py`

**Functions to extract:**
- `calculate_momentum(symbol)` → Returns 1W/1M/1Y momentum

**Current location:** Lines ~360-400 of `market_data.py`

**Estimated size:** ~80 lines

**Dependencies:**
- Uses `fetch_price_at_date()` from `historical.py`
- Uses constants from `common.constants`

**Steps:**
1. Create `calculations/momentum.py`
2. Move `calculate_momentum()` function
3. Import from `common.constants`, `historical`
4. Update `market_data.py` imports
5. Run tests

### Extract `calculations/volatility.py`

**Functions to extract:**
- `calculate_idio_vol(symbol)` → Returns idio vol, total vol, beta

**Current location:** Lines ~430-470 of `market_data.py`

**Estimated size:** ~60 lines

**Dependencies:**
- Uses `fetch_ticker_and_market()` from `historical.py`
- Uses numpy for regression
- Uses constants from `common.constants`

**Steps:**
1. Create `calculations/volatility.py`
2. Move `calculate_idio_vol()` function
3. Import from `common.constants`, `historical`, numpy
4. Update `market_data.py` imports
5. Run tests

### Extract `calculations/technical.py`

**Functions to extract:**
- `calculate_rsi(prices, period=14)` → Returns RSI value

**Current location:** Lines ~400-425 of `market_data.py`

**Estimated size:** ~30 lines

**Dependencies:**
- Uses numpy for delta calculations
- Uses `RSI_PERIOD` from `common.constants`

**Steps:**
1. Create `calculations/technical.py`
2. Move `calculate_rsi()` function
3. Import from `common.constants`, numpy
4. Update `market_data.py` imports
5. Run tests

---

## 🚧 Phase 4: Services (TODO)

### Extract `services/markets.py`

**Functions to extract:**
- `get_markets_data()` → Fetch all market overview data
- `get_market_snapshot(categories, show_momentum)` → Generic market data fetcher
- `get_ticker_data(symbol, include_momentum)` → Basic ticker data
- `get_ticker_full_data(symbol)` → Full ticker data
- `get_ticker_history(symbol, period)` → Historical price data

**Current location:** Lines ~500-650 of `market_data.py`

**Estimated size:** ~200 lines

**Dependencies:**
- yfinance
- Constants from `common.constants`
- Calculations from `calculations/`
- Date utils from `common.dates`

**Steps:**
1. Create `services/markets.py`
2. Move market data fetching functions
3. Import dependencies
4. Update `market_data.py` imports
5. Run tests

### Extract `services/sectors.py`

**Functions to extract:**
- `get_sector_data(name)` → Fetch sector ETF + holdings

**Current location:** Lines ~810-920 of `market_data.py`

**Estimated size:** ~150 lines

**Dependencies:**
- yfinance
- pandas (for holdings DataFrame)
- ThreadPoolExecutor (parallel fetching)
- Constants from `common.constants`
- Calculations from `calculations/momentum.py`

**Steps:**
1. Create `services/sectors.py`
2. Move `get_sector_data()` function
3. Import dependencies
4. Update `market_data.py` imports
5. Run tests

### Extract `services/tickers.py`

**Functions to extract:**
- `get_ticker_screen_data(symbol)` → Single ticker comprehensive data
- `get_ticker_screen_data_batch(symbols)` → Batch ticker data (uses yf.Tickers)

**Current location:** Lines ~1000-1180 of `market_data.py`

**Estimated size:** ~200 lines

**Dependencies:**
- yfinance (including yf.Tickers batch API)
- All calculations (momentum, volatility, RSI)
- Constants from `common.constants`

**Steps:**
1. Create `services/tickers.py`
2. Move ticker data functions
3. Import dependencies
4. Update `market_data.py` imports
5. Run tests

### Extract `services/options.py`

**Functions to extract:**
- `get_options_data(symbol, expiration)` → Comprehensive options chain analysis

**Current location:** Lines ~1600-1900 of `market_data.py`

**Estimated size:** ~350 lines (complex function)

**Dependencies:**
- yfinance
- pandas (for options chain DataFrames)
- numpy (for calculations)
- datetime/timedelta
- Constants from `common.constants`

**Steps:**
1. Create `services/options.py`
2. Move `get_options_data()` function
3. Import dependencies
4. Update `market_data.py` imports
5. Run tests

### Extract `services/news.py`

**Functions to extract:**
- `get_news_data(symbol)` → Fetch news articles

**Current location:** Lines ~1510-1525 of `market_data.py`

**Estimated size:** ~20 lines (simple function)

**Dependencies:**
- yfinance

**Steps:**
1. Create `services/news.py`
2. Move `get_news_data()` function
3. Update `market_data.py` imports
4. Run tests

---

## 🚧 Phase 5: Formatters (TODO)

### Extract `formatters/markets.py`

**Functions to extract:**
- `format_markets(data)` → Markets overview screen formatter
- `format_market_snapshot(data)` → Generic market snapshot formatter

**Current location:** Lines ~690-810 and ~1430-1510 of `market_data.py`

**Estimated size:** ~250 lines

**Dependencies:**
- Constants from `common.constants` (DISPLAY_NAMES, FORMATTING_SECTIONS, etc.)
- Date utils from `common.dates` (is_market_open, get_market_status)
- datetime/ZoneInfo

**Steps:**
1. Create `formatters/markets.py`
2. Move formatting functions
3. Import dependencies
4. Update `market_data.py` imports
5. Run tests

### Extract `formatters/sectors.py`

**Functions to extract:**
- `format_sector(data)` → Sector drill-down formatter

**Current location:** Lines ~920-1000 of `market_data.py`

**Estimated size:** ~100 lines

**Dependencies:**
- Constants from `common.constants`
- datetime/ZoneInfo

**Steps:**
1. Create `formatters/sectors.py`
2. Move `format_sector()` function
3. Import dependencies
4. Update `market_data.py` imports
5. Run tests

### Extract `formatters/tickers.py`

**Functions to extract:**
- `format_ticker(data)` → Single ticker detailed view
- `format_ticker_batch(data_list)` → Batch comparison table

**Current location:** Lines ~1180-1430 of `market_data.py`

**Estimated size:** ~280 lines

**Dependencies:**
- Constants from `common.constants` (BETA thresholds, IDIO_VOL thresholds, RSI thresholds)
- datetime/ZoneInfo

**Steps:**
1. Create `formatters/tickers.py`
2. Move ticker formatting functions
3. Import dependencies
4. Update `market_data.py` imports
5. Run tests

### Extract `formatters/options.py`

**Functions to extract:**
- `format_options(data)` → Comprehensive options chain formatter
- `format_options_summary(data)` → Brief options summary for ticker screen

**Current location:** Lines ~1900-2230 of `market_data.py`

**Estimated size:** ~350 lines

**Dependencies:**
- datetime/ZoneInfo
- No constants needed (all data passed in)

**Steps:**
1. Create `formatters/options.py`
2. Move options formatting functions
3. Import dependencies
4. Update `market_data.py` imports
5. Run tests

### Extract `formatters/news.py`

**Functions to extract:**
- `format_news(data)` → News articles formatter

**Current location:** Lines ~1530-1600 of `market_data.py`

**Estimated size:** ~75 lines

**Dependencies:**
- datetime/ZoneInfo

**Steps:**
1. Create `formatters/news.py`
2. Move `format_news()` function
3. Import dependencies
4. Update `market_data.py` imports
5. Run tests

---

## 🚧 Phase 6: Final Cleanup (TODO)

### 6.1 Update `market_data.py` to Re-export Everything

After all extractions, `market_data.py` becomes a **compatibility shim** that re-exports everything:

```python
"""
Market data - compatibility shim.

All functionality moved to submodules:
- common/constants.py - Constants and mappings
- common/dates.py - Market hours utilities
- common/symbols.py - Symbol normalization
- calculations/ - Momentum, volatility, RSI
- services/ - Data fetching (markets, sectors, tickers, options, news)
- formatters/ - BBG Lite text formatting

This file re-exports everything for backward compatibility.
"""

# Re-export common utilities
from mcp_yfinance_ux.common.constants import *  # noqa: F403
from mcp_yfinance_ux.common.dates import *  # noqa: F403
from mcp_yfinance_ux.common.symbols import *  # noqa: F403

# Re-export calculations
from mcp_yfinance_ux.calculations.momentum import *  # noqa: F403
from mcp_yfinance_ux.calculations.technical import *  # noqa: F403
from mcp_yfinance_ux.calculations.volatility import *  # noqa: F403

# Re-export services
from mcp_yfinance_ux.services.markets import *  # noqa: F403
from mcp_yfinance_ux.services.news import *  # noqa: F403
from mcp_yfinance_ux.services.options import *  # noqa: F403
from mcp_yfinance_ux.services.sectors import *  # noqa: F403
from mcp_yfinance_ux.services.tickers import *  # noqa: F403

# Re-export formatters
from mcp_yfinance_ux.formatters.markets import *  # noqa: F403
from mcp_yfinance_ux.formatters.news import *  # noqa: F403
from mcp_yfinance_ux.formatters.options import *  # noqa: F403
from mcp_yfinance_ux.formatters.sectors import *  # noqa: F403
from mcp_yfinance_ux.formatters.tickers import *  # noqa: F403

__all__ = [
    # Constants
    "MARKET_SYMBOLS", "DISPLAY_NAMES", "SECTOR_SYMBOLS",
    # Functions
    "get_markets_data", "format_markets",
    "get_sector_data", "format_sector",
    "get_ticker_screen_data", "get_ticker_screen_data_batch",
    "format_ticker", "format_ticker_batch",
    "get_options_data", "format_options", "format_options_summary",
    "get_news_data", "format_news",
    # ... (complete list)
]
```

**Result:**
- `market_data.py`: 2,045 lines → ~80 lines (just imports)
- No changes needed to `server.py`, `server_http.py`, `cli.py` (backward compatible)

### 6.2 Update `__init__.py` Files

Each package should re-export its public API:

**`common/__init__.py`:**
```python
from .constants import *  # noqa: F403
from .dates import *  # noqa: F403
from .symbols import *  # noqa: F403
```

**`calculations/__init__.py`:**
```python
from .momentum import *  # noqa: F403
from .technical import *  # noqa: F403
from .volatility import *  # noqa: F403
```

**`services/__init__.py`:**
```python
from .markets import *  # noqa: F403
from .news import *  # noqa: F403
from .options import *  # noqa: F403
from .sectors import *  # noqa: F403
from .tickers import *  # noqa: F403
```

**`formatters/__init__.py`:**
```python
from .markets import *  # noqa: F403
from .news import *  # noqa: F403
from .options import *  # noqa: F403
from .sectors import *  # noqa: F403
from .tickers import *  # noqa: F403
```

### 6.3 Run Full Test Suite

```bash
make lint        # All checks must pass
make test        # Unit tests (if any)
./cli markets    # Smoke test
./cli sector technology
./cli ticker TSLA
./cli ticker TSLA F GM
./cli options PALL
./cli news MP
```

### 6.4 Update Documentation

**Files to update:**
- `DEVELOPER.md` - Document new structure
- `README.md` - Note refactored architecture

---

## Estimated Time

**Phase 2 (Common)**: 1-2 hours
**Phase 3 (Calculations)**: 2-3 hours
**Phase 4 (Services)**: 4-6 hours (largest phase)
**Phase 5 (Formatters)**: 3-4 hours
**Phase 6 (Cleanup)**: 1 hour

**Total**: 11-16 hours

---

## Benefits After Complete Refactor

### Maintainability
- Each file ~100-300 lines (vs 2,221 line monolith)
- Clear separation of concerns
- Easy to find code (filename = purpose)
- Single responsibility per module

### Testability
- Can unit test calculations independently
- Can mock services for formatter tests
- Can test date logic without API calls

### Reusability
- Calculations can be used elsewhere
- Services can be called directly
- Formatters can format external data

### Type Safety
- Easier to maintain strict types
- Smaller files = easier to understand types
- mypy runs faster on smaller files

### DRY
- No duplicate constants
- Shared utilities in one place
- Import from single source of truth

---

## Decision: Continue or Stop?

**Option 1: Merge now (Phase 1 only)**
- Constants extracted (biggest win)
- market_data.py reduced by ~180 lines
- Zero breaking changes
- Can continue later

**Option 2: Continue refactor**
- Follow phases 2-6
- 11-16 hours additional work
- Much cleaner codebase
- Breaking changes require careful testing

**Recommendation**: Merge Phase 1 now, continue refactor incrementally when time permits. Constants extraction alone is valuable.

---

## Notes

- All phases are **backward compatible** if `market_data.py` re-exports
- Test after EACH phase (don't batch)
- Commit after EACH successful phase
- Can pause/resume at any phase boundary
- Phase 4 (services) is most complex - budget extra time
