#%%
import pandas as pd
import math
from scipy.stats import norm
from datetime import datetime, timezone
import time
import aiohttp
import asyncio
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
    sigma = iv/100
    if T <= 0:
        # Option expired
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
    
    price_in_coin = price/S
    return price_in_coin

# calculate time to maturity
def calculate_T(expiry_code: str):
    # Convert expiry_code into datetime
    expiry_date = datetime.strptime(expiry_code, "%d%b%y")  

    # Assume expiry is at 08:00 UTC
    expiry_datetime = expiry_date.replace(hour=8, minute=0, second=0).replace(tzinfo=timezone.utc)

    # Get current UTC time
    
    now = datetime.now(timezone.utc)

    # Calculate T in years
    T_seconds = (expiry_datetime - now).total_seconds()
    T = T_seconds / (365.0 * 86400)

    return max(T, 0)  # Return 0 if already expired

# fetch data from Deribit 
async def fetch_option_data(session, instrument_name):
    url = f"https://www.deribit.com/api/v2/public/ticker?instrument_name={instrument_name}"
    try:
        async with session.get(url) as resp:
            data = await resp.json()

            # Handle errors returned by API
            if "error" in data:
                #print(f"[ERROR] {instrument_name}: {data['error']['message']}")
                return (None, None, None)

            result = data.get('result')
            if result is None:
                #print(f"[WARNING] No result for: {instrument_name}")
                return (None, None, None)

            return (
                result.get('mark_iv'),
                result.get('mark_price'),
                result.get('underlying_price')
            )
    except Exception as e:
        print(f"[EXCEPTION] Failed to fetch {instrument_name}: {e}")
        return (None, None, None)

# get mark price of put and call at the same time
async def _get_mark_price_df_async(expiry_code, strike_prices):
    #asset = "BTC"
    r = 0
    TTM = calculate_T(expiry_code)
    results = []

    async with aiohttp.ClientSession() as session:
        for K in strike_prices:
            call_name = f"{asset}-{expiry_code}-{K}-C"
            put_name = f"{asset}-{expiry_code}-{K}-P"

            call_task = fetch_option_data(session, call_name)
            put_task = fetch_option_data(session, put_name)

            mark_iv_c, mark_c, S = await call_task
            mark_iv_p, mark_p, _ = await put_task

            if None in (mark_iv_c, mark_iv_p,S):
                mark_iv_c,S = get_newest_iv_and_index_price()
                mark_iv_p = mark_iv_c

            if None in (mark_iv_c, mark_iv_p,S):
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

def get_newest_iv_and_index_price():
    # Define the API endpoint
    url = "https://www.deribit.com/api/v2/public/get_last_trades_by_currency_and_time"
    
    # Get the current time (now) in milliseconds for the end_timestamp
    end_timestamp = int(datetime.now().timestamp() * 1000)
    
    # Set the start timestamp (e.g., May 1, 2025)
    start_timestamp = int(datetime(2025, 5, 1).timestamp() * 1000)
    
    # Define the request parameters
    params = {
        "currency": asset,  # Specify the currency (e.g., BTC, ETH, etc.)
        "kind": "option",  # Type of instrument (e.g., options)
        "start_timestamp": start_timestamp,  # Start time (in ms)
        "end_timestamp": end_timestamp,  # Current time (in ms)
        "count": 1,  # Retrieve the most recent trade
    }
    
    # Make the API request
    response = requests.get(url, params=params)
    
    # Check if the request was successful and contains the 'result' key
    if response.status_code == 200:
        data = response.json()
        
        # Ensure the 'result' key exists in the response
        if 'result' in data and 'trades' in data['result']:
            trades_data = data['result']['trades']
            
            # Extract the newest trade's implied volatility (IV) and index price
            if trades_data:
                newest_trade = trades_data[0]  # Since we're getting only the most recent trade
                newest_iv = newest_trade['iv']
                index_price = newest_trade['index_price']
                
                return newest_iv, index_price
            else:
                return "No trades found in the specified time range."
        else:
            return "Error: 'result' or 'trades' not found in response."
    else:
        return f"Error in API request: {response.status_code}"
    
# main function which control duration and interval time, return mark price
def run_periodic_task(T1, T2, expiry_code, strike_prices):
    start_time = time.time()
    results_list = []

    while time.time() - start_time < T1:
       
        df = asyncio.run(_get_mark_price_df_async(expiry_code, strike_prices))

        # Save the result with timestamp
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        df['timestamp'] = timestamp      
        results_list.append(df)  

        # Sleep for T2 seconds
        time.sleep(T2)

    return results_list  

#%% input data sample
asset = "BTC" # assume the underlying is BTC
expiry_code = "23MAY25"
strike_prices = [50000, 90000, 100000]
T1 = 10  # run time
T2 = 7  # interval between computation

# run main to get 
result = run_periodic_task(T1, T2, expiry_code, strike_prices)
final_df = pd.concat(result, ignore_index=True)
print(final_df.to_string(index=False))


# %%

