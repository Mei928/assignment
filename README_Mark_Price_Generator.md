#### How to run
1. set the **parameters** in the input section:
    - `asset`: Underlying asset symbol (e.g., `"BTC"`)
    - `expiry_code`: Option expiry date in format like `"23MAY25"`
    - `strike_prices`: List of strike prices, e.g., `[80000, 90000, 100000]`
    - `T1`: Total duration to run the calculation (in seconds)
    - `T2`: Interval between calculations (in seconds)(T2\<T1) 
2. run the script : Mark_Price_Generator.py, the script will:
    - Periodically query Deribit’s public API.
    - Calculate mark prices using Black-Scholes formula.
    - Collect results in a `pandas.DataFrame` with timestamps for every interval
    - print the final combined DataFrame with calculated mark price with deribit mark price for both call and put options, when no deribit mark price available, it shows none.

#### Key challenges
- API: I need to fetch call option and put option data at the same time to make the result accurate, sending multiple requests in parallel.
- Details: Deribit returns implied volatility as percentages, needs to be converted to decimal for correct calculations. Also, the mark price should be based on the underlying asset(eg: BTC), not quoted in USD.
- Errors: Need to manage cases where the specified instrument is not found, leading to API errors.
- Custom strikes: when `mark_iv` is not available, need an alternative source of IV data. 

#### Reasoning
1. The purpose is to generate mark prices for options, which are usually calculated by the Black Scholes (BS) model. After writing the BS model function and testing, the results of BS model are quite similar to the mark price privided by Deribit, so the BS model was chosen. 
2. Input for BS model:
     - Underlying: we need to assign specific underlying in order to fetch data and do calculations, here we assume the underlying to be BTC, for any other coin, the process is the same, we can simply change the variable `asset`
     - Interest rate:  for crypto currency it’s usually 0, also from the output of Deribit we also saw interest rate is 0, so another assumption is zero interest rate.
     - Time to maturity (TTM): we only have the date, so we assume expiry is at 08:00 UTC, which is the usual expiry time of crypto options on Deribit. Then simply calculate the difference between expiry time and now.
     - The underlying price and implied volatility (IV): we need to fetch them from the Deribit API, for call and put, respectively. For standard strikes, I fetch IV from `mark_iv` of the same option, for custom strikes where there is no `mark_iv`, I fetch it from the `iv` of last traded option in that underlying (BTC)
 3. We loop through each strike price for both call and put, fetch the data and do the calculation.
 4. Make sure to fetch the data of put and call at the same time, compare results with Deribit.
 5. Add time interval and duration time.
 6. improve output and details.








