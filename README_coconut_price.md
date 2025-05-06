#### How to run
package required: `pandas` and `requests` .
Run the script: coconut_price.py, the script will:
   - Fetches hourly price data  (past 1 year) for multiple instruments on production and testnet of Deribit.
   - Multiply weight (amount) on each coin's prices to calculate possible coconut prices in USD at every time point.
   - Find the most probable price by looking for the row with the minimal variance.
   - Print the most probable price on both testnet and production net.
 

#### Key challanges
- PAXG data is missing from deribit production before December 2024.
- Define the frequency at which we need the price data.
- how to define the most possible price : minimal variance.

#### Reasoning
1. In the screenshot, the coconut price—regardless of the payment coin—should be the same. That means there must be a point in time where, for each coin, the **amount paid × coin price** equals the same total (i.e., the same coconut price).
2. So we need to retrieve historical price data for all six coins, for each timestamp, we scale the coin prices by the amount paid (the weights). We then look for a timestamp where all the scaled values (i.e., the coconut prices) are as close as possible—ideally equal. I assume the transaction happened within the last year, so I initially pull one year of historical data. If no suitable point is found, I can expand the time range. I use hourly data so the sample size is not too small, but also not too big. 
3. I found that price history for all six coins isn’t available over the full year, but the coconut prices paid in XRP and ADA (7.2942 and 7.3376) are very close, suggesting that XRP and ADA prices were nearly equal at the time of the screenshot, which doesn't happen very often, and it happened before the PAXG price was available on deribit, so I exclude the PAXG from the production net analysis and proceed with the remaining five coins.
4. By calculating the variance of the scaled coconut prices across coins for each timestamp, I identify the time when the prices are most aligned, which is 2024-11-11 at 7am, the corresponding coconut price is around 4.21$ (average of all 5 payments).
5. I then perform the same analysis on testnet, the result is not as good as production net, so we can determine the coconut price is 4.21$.
