"""
NexusTrade — Ticker Search
Provides fuzzy-match search for stock and crypto tickers.
"""

from typing import Optional

# ─── Popular Stock Tickers ─────────────────────────────────────
STOCK_TICKERS = [
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corporation"),
    ("GOOGL", "Alphabet Inc."),
    ("GOOG", "Alphabet Inc. Class C"),
    ("AMZN", "Amazon.com Inc."),
    ("NVDA", "NVIDIA Corporation"),
    ("META", "Meta Platforms Inc."),
    ("TSLA", "Tesla Inc."),
    ("BRK.B", "Berkshire Hathaway Inc."),
    ("JPM", "JPMorgan Chase & Co."),
    ("V", "Visa Inc."),
    ("JNJ", "Johnson & Johnson"),
    ("UNH", "UnitedHealth Group Inc."),
    ("HD", "Home Depot Inc."),
    ("PG", "Procter & Gamble Co."),
    ("MA", "Mastercard Inc."),
    ("XOM", "Exxon Mobil Corporation"),
    ("CVX", "Chevron Corporation"),
    ("LLY", "Eli Lilly and Company"),
    ("ABBV", "AbbVie Inc."),
    ("MRK", "Merck & Co. Inc."),
    ("PFE", "Pfizer Inc."),
    ("AVGO", "Broadcom Inc."),
    ("COST", "Costco Wholesale Corporation"),
    ("KO", "Coca-Cola Company"),
    ("PEP", "PepsiCo Inc."),
    ("TMO", "Thermo Fisher Scientific"),
    ("WMT", "Walmart Inc."),
    ("MCD", "McDonald's Corporation"),
    ("CRM", "Salesforce Inc."),
    ("CSCO", "Cisco Systems Inc."),
    ("ACN", "Accenture plc"),
    ("ABT", "Abbott Laboratories"),
    ("DHR", "Danaher Corporation"),
    ("LIN", "Linde plc"),
    ("CMCSA", "Comcast Corporation"),
    ("ADBE", "Adobe Inc."),
    ("NKE", "Nike Inc."),
    ("TXN", "Texas Instruments Inc."),
    ("NFLX", "Netflix Inc."),
    ("AMD", "Advanced Micro Devices"),
    ("INTC", "Intel Corporation"),
    ("QCOM", "Qualcomm Inc."),
    ("ORCL", "Oracle Corporation"),
    ("IBM", "International Business Machines"),
    ("GE", "General Electric Co."),
    ("CAT", "Caterpillar Inc."),
    ("BA", "Boeing Company"),
    ("RTX", "RTX Corporation"),
    ("GS", "Goldman Sachs Group"),
    ("MS", "Morgan Stanley"),
    ("BLK", "BlackRock Inc."),
    ("SCHW", "Charles Schwab Corp."),
    ("SPGI", "S&P Global Inc."),
    ("AXP", "American Express Co."),
    ("C", "Citigroup Inc."),
    ("BAC", "Bank of America Corp."),
    ("WFC", "Wells Fargo & Co."),
    ("USB", "U.S. Bancorp"),
    ("PNC", "PNC Financial Services"),
    ("T", "AT&T Inc."),
    ("VZ", "Verizon Communications"),
    ("TMUS", "T-Mobile US Inc."),
    ("DIS", "Walt Disney Company"),
    ("PYPL", "PayPal Holdings Inc."),
    ("SQ", "Block Inc."),
    ("UBER", "Uber Technologies Inc."),
    ("ABNB", "Airbnb Inc."),
    ("SNAP", "Snap Inc."),
    ("PINS", "Pinterest Inc."),
    ("SPOT", "Spotify Technology"),
    ("ZM", "Zoom Video Communications"),
    ("SHOP", "Shopify Inc."),
    ("SE", "Sea Limited"),
    ("BABA", "Alibaba Group"),
    ("JD", "JD.com Inc."),
    ("NIO", "NIO Inc."),
    ("RIVN", "Rivian Automotive"),
    ("LCID", "Lucid Group Inc."),
    ("F", "Ford Motor Company"),
    ("GM", "General Motors Co."),
    ("PLTR", "Palantir Technologies"),
    ("SNOW", "Snowflake Inc."),
    ("NET", "Cloudflare Inc."),
    ("DDOG", "Datadog Inc."),
    ("CRWD", "CrowdStrike Holdings"),
    ("ZS", "Zscaler Inc."),
    ("PANW", "Palo Alto Networks"),
    ("FTNT", "Fortinet Inc."),
    ("NOW", "ServiceNow Inc."),
    ("WDAY", "Workday Inc."),
    ("TEAM", "Atlassian Corp."),
    ("MDB", "MongoDB Inc."),
    ("COIN", "Coinbase Global Inc."),
    ("HOOD", "Robinhood Markets Inc."),
    ("SOFI", "SoFi Technologies"),
    ("AAL", "American Airlines Group"),
    ("DAL", "Delta Air Lines Inc."),
    ("UAL", "United Airlines Holdings"),
    ("LUV", "Southwest Airlines Co."),
    ("SPY", "SPDR S&P 500 ETF Trust"),
    ("QQQ", "Invesco QQQ Trust"),
    ("DIA", "SPDR Dow Jones ETF"),
    ("IWM", "iShares Russell 2000 ETF"),
    ("VTI", "Vanguard Total Stock ETF"),
    ("VOO", "Vanguard S&P 500 ETF"),
    ("ARKK", "ARK Innovation ETF"),
    ("GLD", "SPDR Gold Shares"),
    ("SLV", "iShares Silver Trust"),
    ("USO", "United States Oil Fund"),
]

# ─── Popular Crypto Pairs ──────────────────────────────────────
CRYPTO_TICKERS = [
    ("BTC", "Bitcoin"),
    ("ETH", "Ethereum"),
    ("BNB", "Binance Coin"),
    ("XRP", "Ripple"),
    ("ADA", "Cardano"),
    ("SOL", "Solana"),
    ("DOGE", "Dogecoin"),
    ("DOT", "Polkadot"),
    ("AVAX", "Avalanche"),
    ("MATIC", "Polygon"),
    ("LINK", "Chainlink"),
    ("UNI", "Uniswap"),
    ("ATOM", "Cosmos"),
    ("LTC", "Litecoin"),
    ("FIL", "Filecoin"),
    ("NEAR", "NEAR Protocol"),
    ("APT", "Aptos"),
    ("ARB", "Arbitrum"),
    ("OP", "Optimism"),
    ("SUI", "Sui"),
    ("TRX", "TRON"),
    ("SHIB", "Shiba Inu"),
    ("PEPE", "Pepe"),
    ("ALGO", "Algorand"),
    ("XLM", "Stellar"),
    ("VET", "VeChain"),
    ("MANA", "Decentraland"),
    ("SAND", "The Sandbox"),
    ("AXS", "Axie Infinity"),
    ("AAVE", "Aave"),
    ("MKR", "Maker"),
    ("CRV", "Curve DAO Token"),
    ("SNX", "Synthetix"),
    ("COMP", "Compound"),
    ("RENDER", "Render Token"),
    ("INJ", "Injective"),
    ("FET", "Fetch.ai"),
    ("RNDR", "Render"),
    ("GRT", "The Graph"),
    ("IMX", "Immutable X"),
]


def search_tickers(query: str, asset_type: str = "all", limit: int = 8) -> list[dict]:
    """
    Search tickers by keyword.
    Matches against both symbol and company name (case-insensitive).
    
    Args:
        query: Search string
        asset_type: "stock", "crypto", or "all"
        limit: Max results to return
    
    Returns:
        List of {symbol, name, type} dicts
    """
    if not query or len(query.strip()) == 0:
        return []

    q = query.upper().strip()
    results: list[dict] = []

    # Choose which lists to search
    sources: list[tuple[list, str]] = []
    if asset_type in ("stock", "all"):
        sources.append((STOCK_TICKERS, "stock"))
    if asset_type in ("crypto", "all"):
        sources.append((CRYPTO_TICKERS, "crypto"))

    for ticker_list, t_type in sources:
        for symbol, name in ticker_list:
            # Match on symbol prefix or name substring
            if symbol.upper().startswith(q) or q in name.upper():
                results.append({
                    "symbol": symbol,
                    "name": name,
                    "type": t_type,
                })

    # Sort: exact symbol prefix matches first, then by symbol length
    results.sort(key=lambda r: (
        0 if r["symbol"].upper().startswith(q) else 1,
        len(r["symbol"]),
    ))

    return results[:limit]
