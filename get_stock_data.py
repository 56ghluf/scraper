from datetime import datetime, timedelta
from time import time

import pandas as pd
import numpy as np
import yfinance as yf

# very important to use THIS string
# it has a non-breaking space (U+00A0)
# why does openinsider.com use one? I have no idea
TRADE_DATE_COL = 'Trade Date'

def custom_str_to_float(x):
    if x == '':
        return float('nan')
    if x == '>999':
        return 1000
    try:
        return float(x)
    except (TypeError, ValueError):
        print(f'FATAL -- custom_str_to_float: could not convert {x} to float')

openinsider_data = pd.read_csv('openinsider_data.csv', delimiter='\x1F', dtype={'Ticker': 'string'}, converters={'1w': custom_str_to_float, '1m': custom_str_to_float, '6m': custom_str_to_float})

openinsider_data = openinsider_data.dropna(subset=['Ticker'])
openinsider_data['Ticker'] = openinsider_data['Ticker'].str.strip()

groups = openinsider_data.groupby(TRADE_DATE_COL)['Ticker'].unique()

def get_end_date(start_date):
    return (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(11)).strftime('%Y-%m-%d')

print('retrieving stock data...\n')
start = time()

stock_data = {}

count = 0
total = len(groups)

for start_date, tickers in groups.items():
    stock_data[start_date] = yf.download(list(tickers), start=start_date, end=get_end_date(start_date), group_by='ticker', progress=False, auto_adjust=False)

    count += 1
    print(f'\rprogres: {count/total*100:.1f}%', end='', flush=True)

delta = time() - start

print(f'\nfinished retrieving stock data in {int(delta // 3600)} hours, {int((delta % 3600) // 60)} minutes, {delta % 60:.2f} seconds')

def get_following_min_max_price(row):
    date = row[TRADE_DATE_COL]
    ticker = row['Ticker']

    curr_stock_data = stock_data[date][ticker]

    if curr_stock_data.empty:
        return pd.Series({'following_10_day_max': np.nan, 'following_10_day_min': np.nan}, dtype='float64')
 
    close_prices = curr_stock_data['Close']
    base = close_prices.iloc[0]

    return pd.Series({'following_10_day_max': close_prices.iloc[2:].max() / base, 'following_10_day_min': close_prices.iloc[2:].min() / base})

openinsider_data[['following_10_day_max', 'following_10_day_min']] = openinsider_data.apply(get_following_min_max_price, axis=1)

print(openinsider_data.info())
openinsider_data.to_csv('insider_trading_data.csv', sep='\x1F', index=False)

print('finished processing stock data and wrote to disk')