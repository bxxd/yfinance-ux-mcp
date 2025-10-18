# Feature: Watchlist Support

**Status**: Planned (not started)

**Context**: All major financial interfaces (Bloomberg, Yahoo Finance, Google Finance) have two key sections:
1. General market overview (organized by sector/region/asset class)
2. Personalized watchlist/portfolio

We currently have #1 (general market data), but not #2 (watchlist).

**Reference**: See `../tmp/finance-examples/` for screenshots showing:
- Google Finance: "Top movers in your lists"
- Yahoo Finance: "My Watchlist"
- Bloomberg: Portfolio tracking

## Proposal

Add ability to define custom watchlists:
- Call via: `categories=['watchlist']` or similar
- Challenge: Tools are stateless, watchlists need persistence

## Open Questions

1. Where to persist watchlist data? (config file? separate service?)
2. Should this be an MCP tool feature, or part of broader investment tracking system?
3. Format: Simple ticker list, or richer (with notes, entry price, etc.)?
4. Multiple watchlists? (e.g., 'tech-watchlist', 'crypto-watchlist')

## Next Steps (when we tackle this)

1. Decide on persistence strategy
2. Design watchlist schema
3. Add `categories=['watchlist']` support
4. Update tool description with watchlist examples
5. Test with CLI

## Related Ideas

- Sector-based categories (tech, healthcare, energy, financials)
- Named watchlists with metadata
- Integration with broader portfolio tracking
