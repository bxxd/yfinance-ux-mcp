# yfinance-fetcher Library

**One source of truth for yfinance fetching logic**

## Architecture: Separation of Concerns

```
mcp-yfinance-ux/lib/yfinance_fetcher.py        ← CANONICAL SOURCE (one source of truth)
    ↓ (imported by MCP server)
mcp_yfinance_ux/historical.py                  ← MCP server imports from lib/
    ↓ (copied via agent-tools/bin/import-yfinance-lib.sh)
agent-tools/subagents/portfolio/workspace/portfolio/scripts/yfinance_fetcher.py
    ↓ (make build)
agent-tools/workspace/dist/portfolio/scripts/yfinance_fetcher.py
    ↓ (deploy to tenants)
/var/idio-shared/{env}/{user}/portfolio/scripts/yfinance_fetcher.py
    ↑ (import)
portfolio/update-portfolio.py                  ← Consumer
```

## One Source of Truth

**Edit here**: `mcp-yfinance-ux/lib/yfinance_fetcher.py`

**Used by**:
1. MCP server (`mcp_yfinance_ux/historical.py` imports from `../lib/`)
2. Portfolio update scripts (imports from deployed `portfolio/scripts/`)
3. Any portfolio workspace Python code needing reliable yfinance fetching

## Key Insight

Uses **individual `yf.Ticker().history()` calls with ThreadPoolExecutor** (RELIABLE)
NOT `yf.download()` batch API (UNRELIABLE - timeouts kill entire batch)

This pattern proven in MCP server production use.

## Packaging & Deployment

This repo (mcp-yfinance-ux) is PUBLIC - it knows nothing about private infrastructure.

**For internal deployment to tenant workspaces:**

### 1. Edit the canonical source (here)
```bash
cd /home/ubuntu/idio/mcp-yfinance-ux
vim lib/yfinance_fetcher.py
```

### 2. Import to agent-tools (private infrastructure)
```bash
cd /home/ubuntu/idio/agent-tools
./bin/import-yfinance-lib.sh
# Copies lib/yfinance_fetcher.py → subagents/portfolio/workspace/portfolio/scripts/
```

### 3. Build agent-tools
```bash
cd /home/ubuntu/idio/agent-tools
make build
# Creates workspace/dist/portfolio/scripts/yfinance_fetcher.py
```

### 4. Deploy to tenants (ALWAYS ASK USER FIRST!)
```bash
# Test in DEV first
cd /home/ubuntu/idio/alpha-server
cargo run --bin tools setup breed --sync

# After DEV testing, deploy to PROD breed (canary)
cd /home/ubuntu/idio/prod/alpha-server
cargo run --bin tools setup breed --sync

# After PROD breed validation, deploy to other users
cargo run --bin tools setup <username> --sync
```

## Usage in Portfolio Script

```python
import sys
from pathlib import Path

# Add scripts/ to path (library is in portfolio/scripts/)
scripts_path = Path(__file__).parent / "scripts"
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))

from yfinance_fetcher import fetch_multiple_histories

# Use it
symbols = ['AAPL', 'TSLA', 'MP']
histories = fetch_multiple_histories(symbols, months=12)

for symbol, hist in histories.items():
    if not hist.empty:
        current_price = hist['Close'].iloc[-1]
        print(f"{symbol}: ${current_price:.2f}")
```

## Maintenance

**When fixing bugs or adding features:**
1. Edit `mcp-yfinance-ux/lib/yfinance_fetcher.py` (one source of truth)
2. Run `agent-tools/bin/import-yfinance-lib.sh` (copies to portfolio agent)
3. Build agent-tools: `cd /home/ubuntu/idio/agent-tools && make build`
4. Test MCP server still works: `mcp__yfinance-ux__ticker '{"symbol": "TSLA"}'`
5. Deploy to tenants (ALWAYS ASK USER FIRST): dev → prod breed → all users

**Version sync**: Library is copied during import, not symlinked. Portfolio gets a snapshot.

## Why This Architecture

✅ **One source of truth** - Edit in one place (mcp-yfinance-ux/lib/)
✅ **Separation of concerns** - Library is pure logic, no MCP dependencies
✅ **No runtime coupling** - Deployed copy, not live import
✅ **Clear ownership** - MCP server owns the fetching logic
✅ **Portfolio-specific deployment** - Library lives in portfolio/scripts/, not general workspace

## Testing

Test the library directly:

```bash
cd /home/ubuntu/idio/mcp-yfinance-ux
python3 -c "
import sys
sys.path.insert(0, 'lib')
from yfinance_fetcher import fetch_multiple_histories

histories = fetch_multiple_histories(['AAPL', 'TSLA'], months=12)
for symbol, hist in histories.items():
    if not hist.empty:
        print(f'{symbol}: {len(hist)} rows')
"
```
