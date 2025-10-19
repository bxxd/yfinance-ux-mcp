"""
Core market data functionality - yfinance business logic
Testable independently of MCP protocol layer
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import yfinance as yf  # type: ignore[import-untyped]

# Constants
WEEKEND_START_DAY = 5  # Saturday (Monday = 0, Sunday = 6)

# Category to symbol mappings (for get_market_snapshot)
# Aligned with Paleologo factor framework
CATEGORY_MAPPING: dict[str, list[str]] = {
    "us": ["sp500", "nasdaq", "dow", "russell2000"],
    "futures": ["es_futures", "nq_futures", "ym_futures"],
    "volatility": ["vix"],
    "commodities": ["gold", "oil_wti", "natgas"],
    "rates": ["us10y"],
    "crypto": ["btc", "eth", "sol"],
    "europe": ["stoxx50", "dax", "ftse", "cac40"],
    "asia": ["nikkei", "hangseng", "shanghai"],
    "currencies": ["eurusd", "usdjpy", "usdcny", "gbpusd", "usdcad", "audusd"],
    "bonds": ["us10y", "us2y", "us30y"],
    # Industry factors (GICS sectors)
    "sectors": [
        "tech", "financials", "healthcare", "energy", "consumer_disc",
        "industrials", "materials", "utilities", "consumer_stpl", "real_estate", "communication"
    ],
    # Style factors
    "styles": ["momentum", "value", "growth", "quality", "small_cap"],
    # Convenience aggregates
    "factors": ["vix", "gold", "oil_wti", "natgas", "us10y"],  # Core systematic factors
    "all": [
        "es_futures", "nq_futures", "ym_futures",
        "vix", "gold", "oil_wti", "natgas", "us10y",
        "sp500", "nasdaq", "dow", "russell2000",
        "stoxx50", "dax", "ftse", "cac40",
        "nikkei", "hangseng", "shanghai",
        "btc", "eth", "sol",
        "eurusd", "usdjpy", "usdcny", "gbpusd", "usdcad", "audusd",
        "tech", "financials", "healthcare", "energy", "consumer_disc",
        "industrials", "materials", "utilities", "consumer_stpl", "real_estate", "communication",
        "momentum", "value", "growth", "quality", "small_cap",
    ],
}

# Market snapshot symbol mappings
MARKET_SYMBOLS = {
    # US Indices
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "dow": "^DJI",
    "russell2000": "^RUT",

    # Futures
    "es_futures": "ES=F",      # S&P 500 futures
    "nq_futures": "NQ=F",      # Nasdaq futures
    "ym_futures": "YM=F",      # Dow futures
    "rty_futures": "RTY=F",    # Russell 2000 futures

    # European Indices
    "stoxx50": "^STOXX50E",
    "dax": "^GDAXI",
    "ftse": "^FTSE",
    "cac40": "^FCHI",

    # Asian Indices
    "nikkei": "^N225",
    "hangseng": "^HSI",
    "shanghai": "000001.SS",

    # Crypto
    "btc": "BTC-USD",
    "eth": "ETH-USD",
    "sol": "SOL-USD",

    # Commodities
    "gold": "GC=F",
    "silver": "SI=F",
    "oil_wti": "CL=F",
    "oil_brent": "BZ=F",
    "natgas": "NG=F",

    # Bonds
    "us10y": "^TNX",
    "us2y": "^IRX",
    "us30y": "^TYX",

    # Volatility
    "vix": "^VIX",

    # Currencies
    "eurusd": "EURUSD=X",
    "usdjpy": "JPY=X",
    "usdcny": "CNY=X",
    "gbpusd": "GBPUSD=X",
    "usdcad": "CAD=X",
    "audusd": "AUDUSD=X",

    # Sector ETFs (GICS Industries)
    "tech": "XLK",          # Technology
    "financials": "XLF",    # Financials
    "energy": "XLE",        # Energy
    "healthcare": "XLV",    # Healthcare
    "consumer_disc": "XLY", # Consumer Discretionary
    "consumer_stpl": "XLP", # Consumer Staples
    "industrials": "XLI",   # Industrials
    "utilities": "XLU",     # Utilities
    "materials": "XLB",     # Materials
    "real_estate": "XLRE",  # Real Estate
    "communication": "XLC", # Communication Services

    # Style Factor ETFs
    "momentum": "MTUM",     # iShares MSCI USA Momentum
    "value": "VTV",         # Vanguard Value
    "growth": "VUG",        # Vanguard Growth
    "quality": "QUAL",      # iShares MSCI USA Quality
    "small_cap": "IWM",     # Russell 2000 (size factor)

    # Private Credit / BDCs
    "private_credit": "BIZD",  # VanEck BDC Income ETF (private credit proxy)
}

# Formatting sections (for format_market_snapshot)
# Organized by Paleologo factor framework
FORMATTING_SECTIONS: dict[str, list[str]] = {
    "MARKET": ["sp500", "nasdaq", "dow", "russell2000"],  # During market hours
    "MARKET FUTURES": ["es_futures", "nq_futures", "ym_futures"],  # After hours
    "VOLATILITY": ["vix"],
    "COMMODITIES": ["gold", "oil_wti", "natgas"],
    "RATES": ["us10y"],
    "SECTORS": [
        "tech", "financials", "healthcare", "energy", "consumer_disc",
        "industrials", "materials", "utilities", "consumer_stpl", "real_estate", "communication"
    ],
    "STYLE FACTORS": ["momentum", "value", "growth", "quality", "small_cap"],
    "CRYPTO": ["btc", "eth", "sol"],
    "EUROPE": ["stoxx50", "dax", "ftse", "cac40"],
    "ASIA": ["nikkei", "hangseng", "shanghai"],
    "CURRENCIES": ["eurusd", "usdjpy", "usdcny", "gbpusd", "usdcad", "audusd"],
}

# Section to region mapping (for market status display)
SECTION_REGION_MAP: dict[str, str] = {
    "MARKET": "us",
    "MARKET FUTURES": "us",
    "EUROPE": "europe",
    "ASIA": "asia",
}

# Friendly display names
DISPLAY_NAMES: dict[str, str] = {
    "es_futures": "S&P 500", "nq_futures": "Nasdaq", "ym_futures": "Dow",
    "gold": "Gold", "btc": "Bitcoin", "vix": "VIX",
    "oil_wti": "Oil WTI", "natgas": "Nat Gas",
    "us10y": "US 10Y",
    "sp500": "S&P 500", "nasdaq": "Nasdaq", "dow": "Dow", "russell2000": "Russell 2000",
    "stoxx50": "STOXX 50", "dax": "DAX", "ftse": "FTSE", "cac40": "CAC 40",
    "nikkei": "Nikkei", "hangseng": "Hang Seng", "shanghai": "Shanghai",
    "eth": "Ethereum", "sol": "Solana",
    "eurusd": "EUR/USD", "usdjpy": "USD/JPY", "usdcny": "USD/CNY",
    "gbpusd": "GBP/USD", "usdcad": "USD/CAD", "audusd": "AUD/USD",
    # Sectors
    "tech": "Technology", "financials": "Financials", "healthcare": "Healthcare",
    "energy": "Energy", "consumer_disc": "Cons Discr", "industrials": "Industrials",
    "materials": "Materials", "utilities": "Utilities", "consumer_stpl": "Cons Staples",
    "real_estate": "Real Estate", "communication": "Communication",
    # Style factors
    "momentum": "Momentum", "value": "Value", "growth": "Growth",
    "quality": "Quality", "small_cap": "Small Cap",
    # Private credit
    "private_credit": "Private Credit",
}

# Factor annotations
FACTOR_ANNOTATIONS: dict[str, str] = {
    "gold": "Safe haven",
    "btc": "Risk-on",
    "vix": "Fear gauge",
    "us10y": "Fed policy",
}


def is_market_open() -> bool:
    """Check if US market is currently open (9:30 AM - 4:00 PM ET, Mon-Fri)"""
    now_et = datetime.now(ZoneInfo("America/New_York"))

    # Check if weekend
    if now_et.weekday() >= WEEKEND_START_DAY:
        return False

    # Check if within market hours (9:30 AM - 4:00 PM ET)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

    return market_open <= now_et < market_close


def is_us_market_open() -> bool:
    """Check if US market is currently open (9:30 AM - 4:00 PM ET, Mon-Fri)"""
    return is_market_open()


def is_europe_market_open() -> bool:
    """Check if European markets are open (9:00 AM - 5:30 PM CET, Mon-Fri)"""
    now_cet = datetime.now(ZoneInfo("Europe/Paris"))

    # Check if weekend
    if now_cet.weekday() >= WEEKEND_START_DAY:
        return False

    # Check if within market hours (9:00 AM - 5:30 PM CET)
    market_open = now_cet.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now_cet.replace(hour=17, minute=30, second=0, microsecond=0)

    return market_open <= now_cet < market_close


def is_asia_market_open() -> bool:
    """Check if Asian markets are open (9:00 AM - 3:00 PM JST for Tokyo, Mon-Fri)"""
    now_jst = datetime.now(ZoneInfo("Asia/Tokyo"))

    # Check if weekend
    if now_jst.weekday() >= WEEKEND_START_DAY:
        return False

    # Check if within market hours (9:00 AM - 3:00 PM JST)
    market_open = now_jst.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now_jst.replace(hour=15, minute=0, second=0, microsecond=0)

    return market_open <= now_jst < market_close


def get_market_status(region: str) -> str:
    """Get market status for a region"""
    status_map = {
        "us": is_us_market_open,
        "europe": is_europe_market_open,
        "asia": is_asia_market_open,
    }

    if region.lower() in status_map:
        is_open = status_map[region.lower()]()
        return "Open" if is_open else "Closed"

    return ""


def calculate_momentum(symbol: str) -> dict[str, float | None]:
    """Calculate trailing returns (1M, 1Y) for momentum analysis"""
    try:
        ticker = yf.Ticker(symbol)
        # Fetch 1 year of history to calculate trailing returns
        hist = ticker.history(period="1y", interval="1d")

        min_history_len = 2
        if hist.empty or len(hist) < min_history_len:
            return {"momentum_1m": None, "momentum_1y": None}

        current_price = hist["Close"].iloc[-1]

        # 1-month momentum (~21 trading days)
        days_1m = min(21, len(hist) - 1)
        price_1m_ago = hist["Close"].iloc[-days_1m - 1]
        momentum_1m = (
            ((current_price - price_1m_ago) / price_1m_ago * 100)
            if price_1m_ago else None
        )

        # 1-year momentum (first available price in history)
        price_1y_ago = hist["Close"].iloc[0]
        momentum_1y = (
            ((current_price - price_1y_ago) / price_1y_ago * 100)
            if price_1y_ago else None
        )

        return {
            "momentum_1m": momentum_1m,
            "momentum_1y": momentum_1y,
        }
    except Exception:
        return {"momentum_1m": None, "momentum_1y": None}


def get_ticker_data(symbol: str, include_momentum: bool = False) -> dict[str, Any]:
    """Fetch current data for a single ticker"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        change_pct = info.get("regularMarketChangePercent")

        result: dict[str, Any] = {
            "symbol": symbol,
            "price": price,
            "change_percent": change_pct,
        }

        # Add momentum data if requested
        if include_momentum:
            momentum = calculate_momentum(symbol)
            result.update(momentum)

        return result
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def get_ticker_full_data(symbol: str) -> dict[str, Any]:
    """Fetch comprehensive ticker data (price, beta, momentum) for markets() screen"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        price = info.get("regularMarketPrice") or info.get("currentPrice")
        change_pct = info.get("regularMarketChangePercent")
        beta = info.get("beta")

        # Get momentum
        momentum = calculate_momentum(symbol)

        return {
            "symbol": symbol,
            "price": price,
            "change_percent": change_pct,
            "beta": beta,
            "momentum_1m": momentum.get("momentum_1m"),
            "momentum_1y": momentum.get("momentum_1y"),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def get_market_snapshot(
    categories: list[str],
    show_momentum: bool = False
) -> dict[str, dict[str, Any]]:
    """Get snapshot of multiple market categories"""
    # Auto-detect: if no categories specified, show comprehensive global view with factors
    if not categories:
        if is_market_open():
            categories = ["us", "volatility", "commodities", "rates", "sectors", "styles",
                         "crypto", "europe", "asia", "currencies"]
        else:
            categories = ["futures", "volatility", "commodities", "rates", "sectors", "styles",
                         "crypto", "europe", "asia", "currencies"]

    # Build symbol list based on categories
    symbols_to_fetch: list[str] = []
    for cat in categories:
        category = cat.lower()
        # Performance: O(1) dict lookup instead of if/elif chain
        if category in CATEGORY_MAPPING:
            symbols_to_fetch.extend(CATEGORY_MAPPING[category])
        elif category in MARKET_SYMBOLS:
            # Check if it's a specific symbol key
            symbols_to_fetch.append(category)

    # Build list of (key, symbol) pairs to fetch
    fetch_list = [
        (key, symbol)
        for key in symbols_to_fetch
        if (symbol := MARKET_SYMBOLS.get(key)) is not None
    ]

    # Fetch data in parallel using ThreadPoolExecutor
    # Performance: Parallel I/O (network requests) instead of sequential
    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all fetch tasks
        future_to_key = {
            executor.submit(get_ticker_data, symbol, show_momentum): key
            for key, symbol in fetch_list
        }

        # Collect results as they complete
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = {"symbol": key, "error": str(e)}

    return results


def get_ticker_history(symbol: str, period: str = "1mo") -> dict[str, Any]:
    """Get historical price data for a ticker"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        if hist.empty:
            return {"error": f"No historical data found for {symbol}"}

        return {
            "symbol": symbol,
            "period": period,
            "data": hist.to_dict("records"),
            "start_date": hist.index[0].isoformat(),
            "end_date": hist.index[-1].isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UI-BASED SCREENS (not API)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def get_markets_data() -> dict[str, dict[str, Any]]:
    """Fetch all market data for markets() screen - complete market overview"""
    # Symbols to fetch - all market factors
    symbols_to_fetch = [
        # US Equities
        ("sp500", "^GSPC"),
        ("nasdaq", "^IXIC"),
        ("dow", "^DJI"),
        ("russell2000", "^RUT"),
        # Global
        ("stoxx50", "^STOXX50E"),
        ("nikkei", "^N225"),
        ("shanghai", "000001.SS"),
        # Sectors (all 11 GICS)
        ("tech", "XLK"),
        ("financials", "XLF"),
        ("healthcare", "XLV"),
        ("energy", "XLE"),
        ("consumer_disc", "XLY"),
        ("consumer_stpl", "XLP"),
        ("industrials", "XLI"),
        ("utilities", "XLU"),
        ("materials", "XLB"),
        ("real_estate", "XLRE"),
        ("communication", "XLC"),
        # Styles
        ("momentum", "MTUM"),
        ("value", "VTV"),
        ("growth", "VUG"),
        ("quality", "QUAL"),
        ("small_cap", "IWM"),
        # Private Credit
        ("private_credit", "BIZD"),
        # Commodities
        ("gold", "GC=F"),
        ("oil_wti", "CL=F"),
        ("natgas", "NG=F"),
        # Volatility & Rates
        ("vix", "^VIX"),
        ("us10y", "^TNX"),
    ]

    # Fetch in parallel
    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_key = {
            executor.submit(get_ticker_full_data, symbol): key
            for key, symbol in symbols_to_fetch
        }

        for future in as_completed(future_to_key):
            key = future_to_key[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = {"symbol": key, "error": str(e)}

    return results


def format_markets(data: dict[str, dict[str, Any]]) -> str:  # noqa: PLR0915
    """Format markets() screen - BBG Lite style with factors"""
    now = datetime.now(ZoneInfo("America/New_York"))
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M %Z")

    # Header
    market_status = "Market hours" if is_market_open() else "After hours"
    lines = [f"MARKETS {date_str} {time_str} | {market_status}", ""]

    # Helper to format line with ticker symbol
    def format_line(key: str, show_ticker: bool = False) -> str | None:
        info = data.get(key)
        if not info or info.get("error"):
            return None

        price = info.get("price")
        change_pct = info.get("change_percent")
        mom_1m = info.get("momentum_1m")
        mom_1y = info.get("momentum_1y")

        if price is None or change_pct is None:
            return None

        name = DISPLAY_NAMES.get(key, key)

        # Get ticker symbol for drill-down
        ticker = MARKET_SYMBOLS.get(key, "")

        # Format: NAME  TICKER  PRICE  CHANGE%  +X.X%  +XX.X%
        if show_ticker:
            line = f"{name:16} {ticker:8} {price:10.2f}   {change_pct:+6.2f}%"
        else:
            line = f"{name:16}          {price:10.2f}   {change_pct:+6.2f}%"

        # Add momentum
        if mom_1m is not None:
            line += f"   {mom_1m:+6.1f}%"
        else:
            line += "          "

        if mom_1y is not None:
            line += f"   {mom_1y:+7.1f}%"

        return line

    # US EQUITIES
    lines.append("US EQUITIES                   PRICE     CHANGE       1M         1Y")
    for key in ["sp500", "nasdaq", "dow", "russell2000"]:
        if line := format_line(key):
            lines.append(line)
    lines.append("")

    # GLOBAL
    lines.append("GLOBAL                        PRICE     CHANGE       1M         1Y")
    for key in ["stoxx50", "nikkei", "shanghai"]:
        if line := format_line(key):
            lines.append(line)
    lines.append("")

    # SECTORS - show ticker for drill-down
    lines.append("SECTORS          TICKER      PRICE     CHANGE       1M         1Y")
    sector_keys = [
        "tech", "financials", "healthcare", "energy", "consumer_disc",
        "consumer_stpl", "industrials", "utilities", "materials",
        "real_estate", "communication"
    ]
    for key in sector_keys:
        if line := format_line(key, show_ticker=True):
            lines.append(line)
    lines.append("")

    # STYLES - show ticker for drill-down
    lines.append("STYLES           TICKER      PRICE     CHANGE       1M         1Y")
    for key in ["momentum", "value", "growth", "quality", "small_cap"]:
        if line := format_line(key, show_ticker=True):
            lines.append(line)
    lines.append("")

    # PRIVATE CREDIT
    lines.append("PRIVATE CREDIT   TICKER      PRICE     CHANGE       1M         1Y")
    if line := format_line("private_credit", show_ticker=True):
        lines.append(line)
    lines.append("")

    # COMMODITIES
    lines.append("COMMODITIES                   PRICE     CHANGE       1M         1Y")
    for key in ["gold", "oil_wti", "natgas"]:
        if line := format_line(key):
            lines.append(line)
    lines.append("")

    # VOLATILITY & RATES
    lines.append("VOLATILITY & RATES            PRICE     CHANGE       1M         1Y")
    for key in ["vix", "us10y"]:
        if line := format_line(key):
            lines.append(line)
    lines.append("")

    # Footer
    lines.append(f"Data as of {date_str} {time_str} | Source: yfinance")
    lines.append("Drill down: sector('technology') | ticker('AAPL')")

    return "\n".join(lines)


def get_sector_data(name: str) -> dict[str, Any]:
    """Fetch sector data for sector() screen"""
    # Normalize sector name: "real estate" -> "real_estate", "technology" -> "tech"
    sector_key = name.lower().replace(" ", "_")

    # Map display names to keys
    name_to_key = {
        "technology": "tech",
        "consumer discretionary": "consumer_disc",
        "consumer staples": "consumer_stpl",
    }

    # Try direct lookup first, then mapping
    if sector_key in name_to_key:
        sector_key = name_to_key[sector_key]

    # Get sector ETF symbol
    sector_symbol = MARKET_SYMBOLS.get(sector_key)
    if not sector_symbol:
        return {"error": f"Unknown sector: {name}"}

    # Get sector ETF data
    sector_data = get_ticker_full_data(sector_symbol)

    # Get top holdings
    try:
        ticker = yf.Ticker(sector_symbol)
        holdings_df = ticker.funds_data.top_holdings

        # Convert to list of dicts with symbol, name, weight
        holdings = []
        for symbol_idx, row in holdings_df.head(10).iterrows():
            holdings.append({
                "symbol": symbol_idx,
                "name": row["Name"],
                "weight": row["Holding Percent"],
            })
    except Exception:
        holdings = []

    return {
        "sector_key": sector_key,
        "sector_name": DISPLAY_NAMES.get(sector_key, sector_key),
        "sector_symbol": sector_symbol,
        "sector_data": sector_data,
        "holdings": holdings,
    }


def format_sector(data: dict[str, Any]) -> str:
    """Format sector() screen - BBG Lite style"""
    if data.get("error"):
        return f"ERROR: {data['error']}"

    sector_name = data["sector_name"]
    sector_symbol = data["sector_symbol"]
    sector_data = data["sector_data"]
    holdings = data["holdings"]

    now = datetime.now(ZoneInfo("America/New_York"))
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M %Z")

    # Header
    price = sector_data.get("price", 0)
    change_pct = sector_data.get("change_percent", 0)
    lines = [
        f"{sector_name.upper()} SECTOR                         {sector_symbol} {price:.2f} {change_pct:+.2f}%",
        ""
    ]

    # Sector factors
    mom_1m = sector_data.get("momentum_1m")
    mom_1y = sector_data.get("momentum_1y")

    lines.append("SECTOR FACTORS")
    if mom_1m is not None:
        lines.append(f"Momentum 1M      {mom_1m:+6.1f}%")
    if mom_1y is not None:
        lines.append(f"Momentum 1Y      {mom_1y:+6.1f}%")
    lines.append("")

    # Top holdings
    if holdings:
        lines.append("TOP HOLDINGS     SYMBOL      WEIGHT")
        for h in holdings:
            symbol = h["symbol"]
            weight_pct = h["weight"] * 100
            # Truncate name to fit
            name = h["name"][:20]
            lines.append(f"{name:20} {symbol:8}    {weight_pct:5.1f}%")
        lines.append("")

    # Footer
    lines.append(f"Data as of {date_str} {time_str} | Source: yfinance")
    lines.append(f"Back: markets() | Drill down: ticker('{holdings[0]['symbol'] if holdings else 'AAPL'}')")

    return "\n".join(lines)


def format_market_snapshot(data: dict[str, dict[str, Any]]) -> str:  # noqa: PLR0912
    """Format market data into concise readable text (BBG Lite style)"""
    now = datetime.now(ZoneInfo("America/New_York"))
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M %Z")

    # Header with timestamp
    lines = [f"MARKETS {date_str} {time_str}"]

    # Determine which market section to show (MARKET vs MARKET FUTURES)
    market_is_open = is_market_open()

    for section_name, symbols in FORMATTING_SECTIONS.items():
        # Skip MARKET section if market closed (show MARKET FUTURES instead)
        if section_name == "MARKET" and not market_is_open:
            continue
        # Skip MARKET FUTURES section if market open (show MARKET instead)
        if section_name == "MARKET FUTURES" and market_is_open:
            continue

        # Check if any symbols in this section are in our data
        section_data = {k: v for k, v in data.items() if k in symbols}
        if not section_data:
            continue

        # Add market status to section header if applicable
        region = SECTION_REGION_MAP.get(section_name)
        if region:
            status = get_market_status(region)
            section_header = f"{section_name} ({status})"
        else:
            section_header = section_name

        lines.append(section_header)
        for symbol, info in section_data.items():
            if info.get("error"):
                display_name = DISPLAY_NAMES.get(symbol, symbol)
                lines.append(f"{display_name:12} ERROR - {info['error']}")
            else:
                price = info.get("price")
                change_pct = info.get("change_percent")
                momentum_1m = info.get("momentum_1m")
                momentum_1y = info.get("momentum_1y")

                # Check if we have momentum data
                has_momentum = momentum_1m is not None or momentum_1y is not None

                if price is not None and change_pct is not None:
                    display_name = DISPLAY_NAMES.get(symbol, symbol)
                    line = f"{display_name:12} {price:10.2f}  {change_pct:+6.2f}%"

                    # Add momentum columns if available
                    if has_momentum:
                        mom_1m_str = (
                            f"{momentum_1m:+6.1f}%" if momentum_1m is not None else "   N/A"
                        )
                        mom_1y_str = (
                            f"{momentum_1y:+6.1f}%" if momentum_1y is not None else "   N/A"
                        )
                        line += f"  {mom_1m_str} (1M)  {mom_1y_str} (1Y)"

                    lines.append(line)
                elif price is not None:
                    display_name = DISPLAY_NAMES.get(symbol, symbol)
                    lines.append(f"{display_name:12} {price:10.2f}")
                else:
                    display_name = DISPLAY_NAMES.get(symbol, symbol)
                    lines.append(f"{display_name:12} N/A")
        lines.append("")  # blank line between sections

    # Footer with guidance
    lines.append("Source: yfinance")
    lines.append(
        "Try: symbol='TSLA' for ticker | categories=['europe'] for regions | "
        "period='3mo' for history"
    )

    return "\n".join(lines)
