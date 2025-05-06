#%%
import pandas as pd
import math
from scipy.stats import norm
from datetime import datetime, timezone
import time
import requests

#%% functions
# return option mark price using Black Scholes model
def black_scholes_price(S, K, T, r, iv, option_type):
    """
    Calculate Black-Scholes option price.

    Parameters:
        S : float       # Spot (index) price
        K : float       # Strike price
        T : float       # Time to maturity in years
        r : float       # Risk-free interest rate (annualized, decimal)
        sigma : float   # Implied volatility (annualized, decimal)
        option_type : str  # 'call' or 'put'

    Returns:
        float : Theoretical option price (mark price)
    """    
    sigma = iv / 100
    if T <= 0:
        if option_type == 'call':
            return max(0.0, S - K)
        else:
            return max(0.0, K - S)

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == 'call':
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    elif option_type == 'put':
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    else:
        raise ValueError("option_type must be 'call' or 'put'")

    return price / S

# calculate time to maturity
def calculate_T(expiry_code: str):
    expiry_date = datetime.strptime(expiry_code, "%d%b%y")
    expiry_datetime = expiry_date.replace(hour=8, minute=0, second=0).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    T_seconds = (expiry_datetime - now).total_seconds()
    T = T_seconds / (365.0 * 86400)
    return max(T, 0)

# fetch data from Deribit 
def fetch_option_data_sync(instrument_name):
    url = f"https://www.deribit.com/api/v2/public/ticker?instrument_name={instrument_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            return (None, None, None)

        result = data.get('result')
        if result is None:
            return (None, None, None)

        return (
            result.get('mark_iv'),
            result.get('mark_price'),
            result.get('underlying_price')
        )
    except Exception as e:
        #print(f"[EXCEPTION] Failed to fetch {instrument_name}: {e}")
        return (None, None, None)

# get mark price of put and call
def get_mark_price(expiry_code, strike_prices):
    r = 0
    TTM = calculate_T(expiry_code)
    results = []

    for K in strike_prices:
        call_name = f"{asset}-{expiry_code}-{K}-C"
        put_name = f"{asset}-{expiry_code}-{K}-P"

        mark_iv_c, mark_c, S = fetch_option_data_sync(call_name)
        mark_iv_p, mark_p, _ = fetch_option_data_sync(put_name)
        
        if None in (mark_iv_c, mark_iv_p,S):
                mark_iv_c,S = get_newest_iv_and_index_price()
                mark_iv_p = mark_iv_c

        if None in (mark_iv_c, mark_iv_p, S):
            continue

        call_price = black_scholes_price(S, K, TTM, r, mark_iv_c, 'call')
        put_price = black_scholes_price(S, K, TTM, r, mark_iv_p, 'put')

        results.append({
            "option_name": f"{asset}-{expiry_code}",
            "Strike": K,
            "mark_IV_call": mark_iv_c,
            "mark_price_call": call_price,
            "deribit_mark_price_call": mark_c,
            "mark_IV_put": mark_iv_p,
            "mark_price_put": put_price,
            "deribit_mark_price_put": mark_p
        })

    return pd.DataFrame(results)

# get implied volatility when mark_iv not available
def get_newest_iv_and_index_price():
    url = "https://www.deribit.com/api/v2/public/get_last_trades_by_currency_and_time"
    end_timestamp = int(datetime.now().timestamp() * 1000)
    start_timestamp = int(datetime(2025, 5, 1).timestamp() * 1000)
    params = {
        "currency": asset,
        "kind": "option",
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "count": 1,
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        trades_data = data.get('result', {}).get('trades', [])
        if trades_data:
            newest_trade = trades_data[0]
            return newest_trade['iv'], newest_trade['index_price']
        else:
            return "No trades found in the specified time range."
    else:
        return f"Error in API request: {response.status_code}"

# main function which control duration and interval time, return mark price
def run_periodic_task(T1, T2, expiry_code, strike_prices):
    start_time = time.time()
    results_list = []

    while time.time() - start_time < T1:
        df = get_mark_price(expiry_code, strike_prices)
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        df['timestamp'] = timestamp
        results_list.append(df)
        time.sleep(T2)

    return results_list

#%% Main
# input data
asset = "BTC" # assume the underlying is BTC
expiry_code = "23MAY25"
strike_prices = [50000, 90000, 100000]
T1 = 10  # total time in seconds
T2 = 7   # interval between fetches in seconds

# return the generated mark price dataframe
result = run_periodic_task(T1, T2, expiry_code, strike_prices)
final_df = pd.concat(result, ignore_index=True)
print(final_df)
# %%
