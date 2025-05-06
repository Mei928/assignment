#%%
import pandas as pd
import requests
import time

#%% functions
# get all the coin prices from Deribit
def fetch_all_prices(url,instruments):
    def fetch_closes(instrument):
        end = int(time.time() * 1000)
        one_year_ms = 365 * 24 * 60 * 60 * 1000 
        start = end - one_year_ms
        params = {
            "instrument_name": instrument,
            "start_timestamp": start,
            "end_timestamp": end,
            "resolution": "60",  # hourly candles
        }
        resp = requests.get(url, params=params).json()
        return resp['result']['ticks'], resp['result']['close']

    data = {}
    timestamps = None

    for name, symbol in instruments.items():
        t, closes = fetch_closes(symbol)
        data[name] = closes
        if timestamps is None:
            timestamps = t

    df = pd.DataFrame(data)
    df['datetime'] = pd.to_datetime(timestamps, unit='ms')
    df.set_index('datetime', inplace=True)
    
    return df

# find the minimal variance row of the prices
def find_min_variance_row(df: pd.DataFrame, weights: list):
    
    df_scaled = df.mul(weights)

    row_variances = df_scaled.var(axis=1)

    min_var_index = row_variances.idxmin()

    return df.loc[min_var_index], df_scaled.loc[min_var_index]

#%% Main
# input for fetching data on both nets
url_test = "https://test.deribit.com/api/v2/public/get_tradingview_chart_data"
url = "https://www.deribit.com/api/v2/public/get_tradingview_chart_data"
instruments_test = {
        "BTC": "BTC_USDC",
        "ETH": "ETH_USDC",
        "XRP": "XRP_USDC",
        "PAXG": "PAXG_USDC",
        "ADA": "ADA_USDC-PERPETUAL",
        "SOL": "SOL_USDC"
    }
instruments_prod = {
        "BTC": "BTC_USDC",
        "ETH": "ETH_USDC",
        "XRP": "XRP_USDC",
        "ADA": "ADA_USDC-PERPETUAL",
        "SOL": "SOL_USDC"
    }

# get the prices over the past year of all coins
df_mainnet = fetch_all_prices(url,instruments_prod)
df_testnet = fetch_all_prices(url_test,instruments_test)

# define the weights(amount) of each coin
weights = [0.00005181, 0.0013371, 7.29, 7.3376, 0.020196]
weights_test = [0.00005181, 0.0013371, 7.29, 0.0015856, 7.3376, 0.020196]

# get the row of minimal variance after scaling the price
_, scaled_row= find_min_variance_row(df_mainnet, weights)
_, scaled_row_test= find_min_variance_row(df_testnet, weights_test)

# results comparison
print("The price estimation of coconut on production：")
print(scaled_row)
print("The price estimation of coconut on testnet：")
print(scaled_row_test)
print("the resulting coconut price:", scaled_row.mean().round(2))


#%%

