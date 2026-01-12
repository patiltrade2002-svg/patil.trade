import streamlit as st
import requests
import pandas as pd

# -----------------------
# FEES
# -----------------------
FEES = {
    "Coinbase": 0.006,
    "Kraken": 0.0026,
    "Bitpanda": 0.0015
}

# -----------------------
# EXCHANGE FUNCTIONS
# -----------------------
def get_coinbase_price(symbol):
    url = f"https://api.coinbase.com/v2/prices/{symbol}-USD/spot"
    r = requests.get(url)
    return float(r.json()["data"]["amount"])

def build_kraken_pair_map():
    url = "https://api.kraken.com/0/public/AssetPairs"
    r = requests.get(url)
    data = r.json()["result"]

    mapping = {}
    for pair_name, pair in data.items():
        if pair["quote"] == "ZUSD":
            base = pair["base"].replace("X", "").replace("Z", "")
            mapping[base] = pair_name
    return mapping

KRAKEN_PAIR_MAP = build_kraken_pair_map()

def get_kraken_price(symbol):
    if symbol not in KRAKEN_PAIR_MAP:
        return None
    pair = KRAKEN_PAIR_MAP[symbol]
    url = f"https://api.kraken.com/0/public/Ticker?pair={pair}"
    r = requests.get(url)
    result = list(r.json()["result"].values())[0]
    return float(result["c"][0])

def get_bitpanda_price(symbol):
    url = "https://api.bitpanda.com/v1/ticker"
    r = requests.get(url)
    data = r.json()
    return float(data[symbol]["USD"])

# -----------------------
# COMMON COINS
# -----------------------
def get_common_coins():
    coinbase = requests.get("https://api.exchange.coinbase.com/products").json()
    kraken = requests.get("https://api.kraken.com/0/public/AssetPairs").json()["result"]
    bitpanda = requests.get("https://api.bitpanda.com/v1/ticker").json()

    cb_coins = {c["base_currency"] for c in coinbase if c["quote_currency"] == "USD"}
    kr_coins = {p["base"].replace("X", "").replace("Z", "") for p in kraken.values() if p["quote"] == "ZUSD"}
    bp_coins = set(bitpanda.keys())

    return cb_coins & kr_coins & bp_coins

common_coins = get_common_coins()

# -----------------------
# ARBITRAGE LOGIC
# -----------------------
def get_all_prices(symbol):
    prices = {}
    try:
        prices["Coinbase"] = get_coinbase_price(symbol)
    except:
        pass
    try:
        price = get_kraken_price(symbol)
        if price:
            prices["Kraken"] = price
    except:
        pass
    try:
        prices["Bitpanda"] = get_bitpanda_price(symbol)
    except:
        pass
    return prices

def calculate_net_profit(buy_price, sell_price, buy_ex, sell_ex):
    return (
        sell_price
        - buy_price
        - buy_price * FEES[buy_ex]
        - sell_price * FEES[sell_ex]
    )

def detect_arbitrage(symbol, prices):
    buy_ex = min(prices, key=prices.get)
    sell_ex = max(prices, key=prices.get)

    buy_price = prices[buy_ex]
    sell_price = prices[sell_ex]

    return {
        "coin": symbol,
        "buy_from": buy_ex,
        "sell_to": sell_ex,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "net_profit": calculate_net_profit(buy_price, sell_price, buy_ex, sell_ex)
    }

# -----------------------
# STREAMLIT UI
# -----------------------
st.title("🚀 Crypto Arbitrage Dashboard")

rows = []

for coin in sorted(common_coins):
    prices = get_all_prices(coin)

    if len(prices) < 2:
        continue

    result = detect_arbitrage(coin, prices)

    if result["net_profit"] > 0:
        rows.append(result)

if rows:
    df = pd.DataFrame(rows).sort_values("net_profit", ascending=False)
    st.dataframe(df)
else:
    st.info("No profitable arbitrage opportunities found.")
