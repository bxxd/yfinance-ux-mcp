"""
Core market data functionality - yfinance business logic
Testable independently of MCP protocol layer
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import yfinance as yf  # type: ignore[import-untyped]

# Constants
WEEKEND_START_DAY = 5  # Saturday (Monday = 0, Sunday = 6)

# Factor thresholds
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
BETA_HIGH_THRESHOLD = 1.2
BETA_LOW_THRESHOLD = 0.8
IDIO_VOL_HIGH_THRESHOLD = 30
IDIO_VOL_LOW_THRESHOLD = 15

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


def calculate_rsi(prices: Any, period: int = RSI_PERIOD) -> float | None:  # noqa: ANN401
    """Calculate RSI (Relative Strength Index) for a price series"""
    try:
        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # Calculate average gains and losses
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Return most recent RSI value
        return float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else None
    except Exception:
        return None


def calculate_idio_vol(symbol: str) -> dict[str, float | None]:
    """Calculate idiosyncratic volatility (stock-specific risk after removing market exposure)"""
    try:
        # Fetch 1 year of daily returns for ticker and market
        ticker = yf.Ticker(symbol)
        market = yf.Ticker("^GSPC")  # S&P 500 as market proxy

        hist_ticker = ticker.history(period="1y", interval="1d")
        hist_market = market.history(period="1y", interval="1d")

        min_history_len = 30
        if hist_ticker.empty or hist_market.empty:
            return {"idio_vol": None, "total_vol": None}

        if len(hist_ticker) < min_history_len or len(hist_market) < min_history_len:
            return {"idio_vol": None, "total_vol": None}

        # Calculate daily returns
        ticker_returns = hist_ticker["Close"].pct_change().dropna()
        market_returns = hist_market["Close"].pct_change().dropna()

        # Align dates (intersection)
        common_dates = ticker_returns.index.intersection(market_returns.index)
        ticker_returns = ticker_returns.loc[common_dates]
        market_returns = market_returns.loc[common_dates]

        if len(ticker_returns) < min_history_len:
            return {"idio_vol": None, "total_vol": None}

        # Total volatility (annualized)
        total_vol = float(ticker_returns.std() * np.sqrt(252) * 100)  # Convert to percentage

        # Linear regression: decompose returns into market (beta) and stock-specific (alpha)
        beta, alpha = np.polyfit(market_returns, ticker_returns, 1)

        # Residuals = idiosyncratic component (stock-specific risk)
        residuals = ticker_returns - (alpha + beta * market_returns)

        # Idiosyncratic volatility (annualized)
        idio_vol = float(residuals.std() * np.sqrt(252) * 100)  # Convert to percentage

        return {
            "idio_vol": idio_vol,
            "total_vol": total_vol,
        }
    except Exception:
        return {"idio_vol": None, "total_vol": None}


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


def format_markets(data: dict[str, dict[str, Any]]) -> str:  # noqa: PLR0912, PLR0915
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
    header = (
        f"{sector_name.upper()} SECTOR                         "
        f"{sector_symbol} {price:.2f} {change_pct:+.2f}%"
    )
    lines = [header, ""]

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
    drill_symbol = holdings[0]["symbol"] if holdings else "AAPL"
    lines.append(f"Back: markets() | Drill down: ticker('{drill_symbol}')")

    return "\n".join(lines)


def get_ticker_screen_data(symbol: str) -> dict[str, Any]:
    """Fetch comprehensive ticker data for ticker() screen"""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # Basic price data
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        change = info.get("regularMarketChange")
        change_pct = info.get("regularMarketChangePercent")
        market_cap = info.get("marketCap")
        volume = info.get("volume")
        name = info.get("longName") or info.get("shortName") or symbol

        # Factor exposures
        beta_spx = info.get("beta")

        # Valuation
        trailing_pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        dividend_yield = info.get("dividendYield")

        # Technicals
        fifty_day_avg = info.get("fiftyDayAverage")
        two_hundred_day_avg = info.get("twoHundredDayAverage")
        fifty_two_week_high = info.get("fiftyTwoWeekHigh")
        fifty_two_week_low = info.get("fiftyTwoWeekLow")

        # Get momentum
        momentum = calculate_momentum(symbol)

        # Get idio vol
        vol_data = calculate_idio_vol(symbol)

        # Calculate RSI
        rsi = None
        try:
            hist = ticker.history(period="1mo", interval="1d")
            if not hist.empty and len(hist) >= RSI_PERIOD:
                rsi = calculate_rsi(hist["Close"])
        except Exception:
            pass

        # Get calendar data (earnings and dividend dates)
        calendar = None
        try:  # noqa: SIM105
            calendar = ticker.calendar
        except Exception:
            pass  # Calendar not available for non-stocks (indices, ETFs, etc.)

        return {
            "symbol": symbol,
            "name": name,
            "price": price,
            "change": change,
            "change_percent": change_pct,
            "market_cap": market_cap,
            "volume": volume,
            "beta_spx": beta_spx,
            "trailing_pe": trailing_pe,
            "forward_pe": forward_pe,
            "dividend_yield": dividend_yield,
            "fifty_day_avg": fifty_day_avg,
            "two_hundred_day_avg": two_hundred_day_avg,
            "fifty_two_week_high": fifty_two_week_high,
            "fifty_two_week_low": fifty_two_week_low,
            "momentum_1m": momentum.get("momentum_1m"),
            "momentum_1y": momentum.get("momentum_1y"),
            "idio_vol": vol_data.get("idio_vol"),
            "total_vol": vol_data.get("total_vol"),
            "rsi": rsi,
            "calendar": calendar,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def format_ticker(data: dict[str, Any]) -> str:  # noqa: PLR0912, PLR0915
    """Format ticker() screen - BBG Lite style with complete factor exposures"""
    if data.get("error"):
        return f"ERROR: {data['error']}"

    symbol = data["symbol"]
    name = data.get("name", symbol)
    price = data.get("price")
    change = data.get("change")
    change_pct = data.get("change_percent")
    market_cap = data.get("market_cap")
    volume = data.get("volume")

    now = datetime.now(ZoneInfo("America/New_York"))
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M %Z")

    lines = []

    # Header
    if price is not None and change is not None and change_pct is not None:
        header = (
            f"{symbol} US EQUITY                   "
            f"LAST PRICE  {price:.2f} {change:+.2f}  {change_pct:+.2f}%"
        )
    else:
        header = f"{symbol} US EQUITY"
    lines.append(header)

    # Company name + Market cap/Volume
    if market_cap is not None and volume is not None:
        # Format market cap (billions)
        market_cap_b = market_cap / 1e9
        volume_m = volume / 1e6
        lines.append(f"{name[:40]:40} MKT CAP  {market_cap_b:6.1f}B    VOLUME {volume_m:5.1f}M")
    else:
        lines.append(name[:60])
    lines.append("")

    # Factor Exposures
    lines.append("FACTOR EXPOSURES")
    beta_spx = data.get("beta_spx")
    if beta_spx is not None:
        sensitivity = ""
        if beta_spx > BETA_HIGH_THRESHOLD:
            sensitivity = "(High sensitivity)"
        elif beta_spx < BETA_LOW_THRESHOLD:
            sensitivity = "(Low sensitivity)"
        lines.append(f"Beta (SPX)       {beta_spx:4.2f}    {sensitivity}")

    idio_vol = data.get("idio_vol")
    total_vol = data.get("total_vol")
    if idio_vol is not None:
        risk_level = ""
        if idio_vol > IDIO_VOL_HIGH_THRESHOLD:
            risk_level = "(High stock-specific risk)"
        elif idio_vol < IDIO_VOL_LOW_THRESHOLD:
            risk_level = "(Low stock-specific risk)"
        lines.append(f"Idio Vol         {idio_vol:4.1f}%   {risk_level}")
    if total_vol is not None:
        lines.append(f"Total Vol        {total_vol:4.1f}%")
    lines.append("")

    # Valuation
    has_valuation = False
    trailing_pe = data.get("trailing_pe")
    forward_pe = data.get("forward_pe")
    dividend_yield = data.get("dividend_yield")

    if any(x is not None for x in [trailing_pe, forward_pe, dividend_yield]):
        lines.append("VALUATION")
        has_valuation = True

    if trailing_pe is not None:
        lines.append(f"P/E Ratio        {trailing_pe:6.2f}")
    if forward_pe is not None:
        lines.append(f"Forward P/E      {forward_pe:6.2f}")
    if dividend_yield is not None:
        lines.append(f"Dividend Yield   {dividend_yield:5.2f}%")

    if has_valuation:
        lines.append("")

    # Earnings and dividend calendar section
    calendar = data.get("calendar")
    has_calendar = False
    if calendar:
        earnings_date = calendar.get("Earnings Date")
        earnings_avg = calendar.get("Earnings Average")
        div_date = calendar.get("Dividend Date")
        ex_div_date = calendar.get("Ex-Dividend Date")

        if earnings_date or div_date or ex_div_date:
            lines.append("CALENDAR")
            has_calendar = True

        if earnings_date and isinstance(earnings_date, list) and earnings_date:
            date_str = earnings_date[0].strftime("%b %d, %Y")
            line = f"Earnings         {date_str}"
            if earnings_avg is not None:
                line += f"  (Est ${earnings_avg:.2f} EPS)"
            lines.append(line)

        if ex_div_date:
            date_str = ex_div_date.strftime("%b %d, %Y")
            lines.append(f"Ex-Dividend      {date_str}")

        if div_date:
            date_str = div_date.strftime("%b %d, %Y")
            lines.append(f"Div Payment      {date_str}")

    if has_calendar:
        lines.append("")

    # Momentum & Technicals
    lines.append("MOMENTUM & TECHNICALS")
    mom_1m = data.get("momentum_1m")
    mom_1y = data.get("momentum_1y")
    if mom_1m is not None:
        lines.append(f"1-Month          {mom_1m:+6.1f}%")
    if mom_1y is not None:
        lines.append(f"1-Year           {mom_1y:+6.1f}%")

    fifty_day = data.get("fifty_day_avg")
    two_hundred_day = data.get("two_hundred_day_avg")
    if fifty_day is not None:
        lines.append(f"50-Day MA        {fifty_day:7.2f}")
    if two_hundred_day is not None:
        lines.append(f"200-Day MA       {two_hundred_day:7.2f}")

    rsi = data.get("rsi")
    if rsi is not None:
        rsi_signal = ""
        if rsi > RSI_OVERBOUGHT:
            rsi_signal = "(Overbought)"
        elif rsi < RSI_OVERSOLD:
            rsi_signal = "(Oversold)"
        lines.append(f"RSI (14D)        {rsi:5.1f}    {rsi_signal}")
    lines.append("")

    # 52-Week Range with visual bar
    fifty_two_high = data.get("fifty_two_week_high")
    fifty_two_low = data.get("fifty_two_week_low")

    if fifty_two_high is not None and fifty_two_low is not None and price is not None:
        lines.append("52-WEEK RANGE")
        lines.append(f"High             {fifty_two_high:7.2f}")
        lines.append(f"Low              {fifty_two_low:7.2f}")

        # Visual bar showing position in range
        range_pct = ((price - fifty_two_low) / (fifty_two_high - fifty_two_low)) * 100
        bar_width = 20
        filled = int((range_pct / 100) * bar_width)
        bar = "=" * filled + "░" * (bar_width - filled)
        lines.append(f"Current          {price:7.2f}  [{bar}]  {range_pct:.0f}% of range")
        lines.append("")

    # Footer
    lines.append(f"Data as of {date_str} {time_str} | Source: yfinance")
    lines.append("Back: markets() | sector('technology')")

    return "\n".join(lines)


def format_ticker_batch(data_list: list[dict[str, Any]]) -> str:
    """Format batch ticker comparison - side-by-side comparison table"""
    if not data_list:
        return "ERROR: No ticker data provided"

    now = datetime.now(ZoneInfo("America/New_York"))
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M %Z")

    lines = []
    lines.append(f"TICKER COMPARISON {date_str} {time_str}")
    lines.append("")

    # Header
    header = (
        f"{'SYMBOL':8} {'NAME':30} {'PRICE':>10} {'CHG%':>8} "
        f"{'BETA':>6} {'IDIO':>6} {'MOM1Y':>8} {'P/E':>8} {'DIV%':>6} {'RSI':>6}"
    )
    lines.append(header)
    lines.append("-" * len(header))

    # Data rows
    for data in data_list:
        if data.get("error"):
            symbol = data.get("symbol", "???")
            lines.append(f"{symbol:8} ERROR: {data['error']}")
            continue

        symbol = data.get("symbol", "")[:8]
        name = data.get("name", "")[:30]
        price = data.get("price")
        change_pct = data.get("change_percent")
        beta_spx = data.get("beta_spx")
        idio_vol = data.get("idio_vol")
        mom_1y = data.get("momentum_1y")
        trailing_pe = data.get("trailing_pe")
        div_yield = data.get("dividend_yield")
        rsi = data.get("rsi")

        # Format each field with proper handling of None
        price_str = f"{price:10.2f}" if price is not None else " " * 10
        chg_str = f"{change_pct:+7.2f}%" if change_pct is not None else " " * 8
        beta_str = f"{beta_spx:6.2f}" if beta_spx is not None else " " * 6
        idio_str = f"{idio_vol:5.1f}%" if idio_vol is not None else " " * 6
        mom_str = f"{mom_1y:+7.1f}%" if mom_1y is not None else " " * 8
        pe_str = f"{trailing_pe:8.2f}" if trailing_pe is not None else " " * 8
        div_str = f"{div_yield:5.2f}%" if div_yield is not None else " " * 6
        rsi_str = f"{rsi:6.1f}" if rsi is not None else " " * 6

        line = (
            f"{symbol:8} {name:30} {price_str} {chg_str} "
            f"{beta_str} {idio_str} {mom_str} {pe_str} {div_str} {rsi_str}"
        )
        lines.append(line)

    lines.append("")
    lines.append(f"Data as of {date_str} {time_str} | Source: yfinance")
    lines.append("Drill down: ticker('TSLA') for detailed analysis")

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
