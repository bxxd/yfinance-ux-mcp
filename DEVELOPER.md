# yfinance MCP Server - Developer Context

Custom Model Context Protocol server for Yahoo Finance data - built for idio project.

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

### 3. Single Flexible Tool

**One tool that adapts > many narrow tools.** Minimize context usage by consolidating functionality.

`get_market_data` handles:
- Market snapshots (auto-detects market hours)
- Individual ticker queries
- Historical price data

**Alternative (worse):** Separate tools for each use case
- `get_futures`
- `get_indices`
- `get_crypto`
- `get_ticker`
- `get_history`

This would consume 5x more context and be harder to use.

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

### Core Functions

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

### MCP Integration

**`list_tools()`** - Defines single tool: `get_market_data`

**`call_tool()`** - Handles three data_types:
- `snapshot` - Market overview (auto-detects or custom categories)
- `current` - Single ticker current price
- `history` - Historical price data

## Testing Approach

### Manual Testing First

```bash
cd /home/ubuntu/idio/yfinance-mcp
poetry run python -c "
from server import get_market_snapshot, format_market_snapshot

data = get_market_snapshot(['futures', 'crypto', 'commodities'])
print(format_market_snapshot(data))
"
```

This must output exactly what you want before wrapping in MCP.

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
├── server.py           # MCP server implementation
├── pyproject.toml      # Poetry dependencies
├── DEVELOPER.md        # This file - developer context
├── CLAUDE.md           # Import reference for Claude Code
└── README.md           # User documentation
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

**Core principle:** Build the simplest thing that solves the real problem, test it manually first, then wrap in MCP matching the manual implementation exactly.

**PMF testing:** Build → Use → Iterate. Real usage reveals what's needed. Speculation adds complexity without value.

**Human-readable output:** Format for humans, not machines. The AI should receive ready-to-use information.

**Single flexible tool:** One tool that adapts beats many narrow tools.

This is infrastructure for investment analysis. Keep it simple, keep it working, extend only when proven necessary.
