from datetime import datetime, timedelta
from time import time, sleep
import logging
from random import random

import pandas as pd
import numpy as np
import yfinance as yf


# === Very simple logging utils ===
def print_debug(msg):
    print('[DEBUG]:', msg)


def print_err(err):
    print('[ERROR]:', err)


# === Loading the openinsider.com dataset ===
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
    except (TypeError, ValueError) as e:
        print_err(f'custom_str_to_float: could not convert {x} to float')
        raise e


openinsider_data = pd.read_csv('openinsider_data.csv',
                               delimiter='\x1F', dtype={'Ticker': 'string'},
                               converters={
                                   '1w': custom_str_to_float,
                                   '1m': custom_str_to_float,
                                   '6m': custom_str_to_float
                               })

openinsider_data = openinsider_data.dropna(subset=['Ticker'])
openinsider_data['Ticker'] = openinsider_data['Ticker'].str.strip()

groups = openinsider_data.groupby(TRADE_DATE_COL)['Ticker'].unique()


# === Download the necessary stock data ===
def get_end_date(start_date):
    return (
        datetime.strptime(start_date, '%Y-%m-%d') + timedelta(11)
    ).strftime('%Y-%m-%d')


def sleep_with_progress(dt):
    start = time()
    curr = 0

    while curr < dt:
        print(f'\rpaused, {int(curr)}s of {
              int(dt)}s [{100*curr/dt:.1f}%]', end='', flush=True)
        sleep(0.2)
        curr = time() - start

    print()


class RateLimitHandler(logging.Handler):
    def __init__(self):
        super().__init__()

        self.caught_rate_limit_error = False

    def emit(self, record):
        if 'YFRateLimitError' in record.getMessage():
            self.caught_rate_limit_error = True

    def reset(self):
        self.caught_rate_limit_error = False

    def __bool__(self):
        return self.caught_rate_limit_error


print_debug('retrieving stock data...\n')
start = time()

stock_data = {}

count = 0
last_pause = 0
total = len(groups)

logger = logging.getLogger('yfinance')
rate_limit_handler = RateLimitHandler()
logger.addHandler(rate_limit_handler)

for start_date, tickers in groups.items():
    retry_attempt = 0

    while True:
        rate_limit_handler.reset()

        result = yf.download(
            list(tickers),
            start=start_date,
            end=get_end_date(start_date),
            group_by='ticker',
            progress=False,
            auto_adjust=False
        )

        if rate_limit_handler:
            print(f'\nattempt {retry_attempt+1} hit rate limit')
            sleep_with_progress(60*2**retry_attempt + 1200 * random())
            retry_attempt += 1
            continue

        stock_data[start_date] = result
        break

    count += 1
    print(f'\rprogress: {count}/{total} [{count/total*100:.1f}%]',
          end='', flush=True)


delta = time() - start

print_debug(('finished retrieving stock data in '
             f'{int(delta // 3600)} hours, '
             f'{int((delta % 3600) // 60)} '
             f'minutes, {delta % 60:.2f} seconds'))


# === Add the downloaded stock data to the dataset ===
def get_following_min_max_price(row):
    date = row[TRADE_DATE_COL]
    ticker = row['Ticker']

    curr_stock_data = stock_data[date][ticker]

    if curr_stock_data.empty:
        return pd.Series({
            'following_10_day_max': np.nan,
            'following_10_day_min': np.nan}, dtype='float64')

    close_prices = curr_stock_data['Close']
    base = close_prices.iloc[0]

    return pd.Series({'following_10_day_max': close_prices.iloc[2:].max() / base, 'following_10_day_min': close_prices.iloc[2:].min() / base})


openinsider_data[['following_10_day_max', 'following_10_day_min']
                 ] = openinsider_data.apply(get_following_min_max_price, axis=1)

openinsider_data.to_csv('insider_trading_data.csv', sep='\x1F', index=False)

print_debug('processed stock data and wrote to disk')
