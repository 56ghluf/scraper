from datetime import datetime, timedelta
from time import time

import pandas as pd
import numpy as np
import yfinance as yf

def custom_str_to_float(x):
    if (x == ''):
        return float('nan')
    if (x == '>999'):
        return 1000
    try:
        return float(x)
    except (TypeError, ValueError):
        print(f'FATAL -- custom_str_to_float: could not convert {x} to float')

openinsider_data = pd.read_csv('openinsider_data.csv', delimiter='\x1F', dtype={'Ticker': 'string'}, converters={'1w': custom_str_to_float, '1m': custom_str_to_float, '6m': custom_str_to_float})

openinsider_data = openinsider_data.dropna(subset=['Ticker'])
openinsider_data['Ticker'] = openinsider_data['Ticker'].str.strip()

count = 0
total = len(openinsider_data)

def get_following_min_max_price(row):
    global count

    # very important to use THIS string
    # it has a non-breaking space (U+00A0)
    # why does openinsider.com use one? I have no idea
    trade_date_col = 'Trade Date'

    start_date = row[trade_date_col]
    end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(11)).strftime('%Y-%m-%d')

    ticker = row['Ticker']

    stock_data = yf.download(ticker, start=start_date, end=end_date, progress=False)

    if stock_data.empty:
        return pd.Series({'following_10_day_max': np.nan, 'following_10_day_min': np.nan}, dtype='float64')

    close_prices = stock_data[('Close', ticker)]
    base = close_prices.iloc[0]

    count += 1
    print(f'\rProgres: {count/total*100:.1f}%', end='', flush=True)

    return pd.Series({'following_10_day_max': close_prices.iloc[2:].max() / base, 'following_10_day_min': close_prices.iloc[2:].min() / base})

print('Retrieving stock data...\n')
start = time()

openinsider_data[['following_10_day_max', 'following_10_day_min']] = openinsider_data.apply(get_following_min_max_price, axis=1)

delta = time() - start

print(f'\nfinished retrieving stock data in {int(delta // 3600)} hours, {int((delta % 3600) // 60)} minutes, {delta % 60:.2f} seconds')

openinsider_data.to_csv('insider_trading_data.csv', sep='\x1F', index=False)