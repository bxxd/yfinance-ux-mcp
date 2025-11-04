"""
Ticker symbol normalization utilities.

Handles Yahoo Finance symbol format conventions:
- Exchange suffixes (NEO.TO, 0700.HK) - keep dots
- Share classes (BRK.B, BRK.A) - convert to hyphens
"""


def normalize_ticker_symbol(symbol: str) -> str:
    """
    Normalize ticker symbol to Yahoo Finance format.

    Exchange suffixes (keep dots):
    - NEO.TO → NEO.TO (Toronto Stock Exchange)
    - 0700.HK → 0700.HK (Hong Kong)
    - RIO.L → RIO.L (London)
    - BHP.AX → BHP.AX (Australia)

    Share classes (convert to hyphens):
    - BRK.B or BRK/B → BRK-B (Berkshire Class B)
    - BRK.A or BRK/A → BRK-A (Berkshire Class A)
    - BAC.PL or BAC/PL → BAC-PL (Preferred stock)

    Heuristic:
    - If dot followed by 2+ uppercase chars: exchange suffix (keep dot)
    - If dot followed by 1-2 chars at end: share class (replace with dash)
    """
    # Replace slashes with hyphens first
    symbol = symbol.replace("/", "-")

    # Check if this is an exchange suffix (dot followed by 2+ uppercase chars)
    # Common exchange suffixes: .TO, .HK, .L, .AX, .PA, .DE, .SW, etc.
    if "." in symbol:
        parts = symbol.split(".")
        # Exchange suffixes are exactly 2 parts, with suffix being 2+ uppercase chars
        if (
            len(parts) == 2  # noqa: PLR2004
            and len(parts[1]) >= 2  # noqa: PLR2004
            and parts[1].isupper()
        ):
            # Exchange suffix - keep the dot
            return symbol
        # Share class - replace dot with dash
        return symbol.replace(".", "-")

    return symbol
