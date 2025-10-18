# Feature: Factor-Aligned Market View

**Status**: Planned (not started)

**Context**: Current market snapshot shows generic categories (futures, crypto, commodities). But users looking at Gold/Bitcoin/Oil are already doing factor analysis - they just don't realize it!

**Insight from Paleologo framework:**
- Returns = Factor (beta/market) + Idiosyncratic (alpha)
- Gold = inflation fear / safe haven factor
- Bitcoin = risk-on / tech sentiment factor
- Oil = energy / inflation factor
- VIX = fear / volatility factor
- 10Y Yield = rate factor

## Current View

```
MARKETS 2025-10-18 | After-hours
US FUTURES
S&P 500         6702.50   +0.51%
...
CRYPTO
Bitcoin       106975.03   +1.71%
...
COMMODITIES
Gold            4213.30   -2.12%
...
```

Generic categories, no factor interpretation.

## Proposed Factor View

```
MARKETS 2025-10-18 | After-hours

BROAD MARKET FACTOR
S&P 500         6702.50   +0.51%
Nasdaq         24986.50   +0.63%
Dow            46381.00   +0.48%

RISK FACTORS
Gold            4213.30   -2.12%  Safe haven
Bitcoin       106975.03   +1.71%  Risk-on
VIX               20.78   -4.53%  Fear gauge

COMMODITY FACTORS
Oil WTI           57.15   +0.28%
Nat Gas            3.01   +2.38%

RATE FACTOR
US 10Y Yield      4.89%   +0.05   Fed policy

TOP IDIO MOVERS (stock-specific alpha)
TSLA              439.31   +2.46%
NVDA              142.50   +3.20%
AAPL              252.29   +1.96%

Data as of 2025-10-18 10:48 EDT | Source: yfinance
Try: symbol='TSLA' for ticker | categories=['europe'] for regions | period='3mo' for history
```

## Benefits

1. **Intuitive**: Looks familiar (still a market snapshot)
2. **Paleologo-aligned**: Explicitly frames through factor lens
3. **Educational**: Shows what factors actually are
4. **Actionable**: "Top Idio Movers" highlights stock-specific opportunities

## Implementation Steps

### Phase 1: Relabel existing data
- [x] Rename "US FUTURES" → "BROAD MARKET FACTOR"
- [ ] Rename "CRYPTO" → "RISK FACTORS" (add annotations)
- [ ] Rename "COMMODITIES" → "COMMODITY FACTORS"
- [ ] Add annotations (Safe haven, Risk-on, Fear gauge, etc.)

### Phase 2: Add missing factors
- [ ] Add VIX (^VIX) to RISK FACTORS
- [ ] Add US 10Y Yield (^TNX) as "RATE FACTOR" section
- [ ] Add US 2Y Yield (^IRX) for yield curve

### Phase 3: Top Idio Movers
- [ ] Define "top movers" logic (e.g., top 3 by absolute % change)
- [ ] Add new section "TOP IDIO MOVERS"
- [ ] Initially: raw % change (no factor adjustment yet)
- [ ] Future: Calculate idio component after factor decomposition

### Phase 4: Factor decomposition (advanced)
- [ ] Calculate beta to S&P 500 for each stock
- [ ] Separate returns into factor + idio components
- [ ] Show: `TSLA +2.46% (Factor: +0.66%, Idio: +1.80%)`
- [ ] This requires historical data and correlation analysis

## Open Questions

1. **Top movers data source**: How to get intraday top movers?
   - Option A: Fetch top N symbols from a predefined list
   - Option B: Use yfinance screener (if available)
   - Option C: Maintain a universe of tickers to check

2. **Factor annotation style**:
   - Inline labels? `Gold  4213.30  -2.12%  Safe haven`
   - Separate column? Grouped differently?

3. **Scope creep**: Is Phase 4 (real factor decomposition) too complex for now?
   - Start with Phase 1-3 (relabeling + adding factors + raw top movers)?
   - Phase 4 can be separate tool later?

4. **Performance**: Fetching many tickers for "top movers" could be slow
   - Need to test with ~50-100 ticker universe
   - Optimize or limit to smaller set?

## Related Tasks

- `watchlist-support.md` - Personal watchlist for tracking idio positions
- Sector categories - Could be organized as "SECTOR FACTORS"

## References

- Paleologo framework: `meta/MISSION.md`
- Factor decomposition theory: Returns = Beta * Market + Idio
- Bloomberg screenshots: `../tmp/finance-examples/`
