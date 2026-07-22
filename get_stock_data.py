from datetime import datetime, timedelta
from time import time, sleep
from random import random

import pandas as pd
import yfinance as yf
from curl_cffi.requests.exceptions import HTTPError, Timeout


# === Very simple logging utils ===
def print_debug(msg):
    print('[DEBUG]:', msg)


def print_err(err):
    print('[ERROR]:', err)


def print_sep(sep='=', count=50):
    print(count*sep)


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

print(f'initial df is of size {len(openinsider_data)}')


# === Download the necessary stock data ===
def get_end_date(start_date):
    return (
        datetime.strptime(start_date, '%Y-%m-%d') + timedelta(11)
    ).strftime('%Y-%m-%d')


def sleep_with_progress(dt):
    start = time()
    curr = 0

    while curr < dt:
        sleep(0.2)
        curr = time() - start
        print(f'\rpaused, {int(curr)}s of {
              int(dt)}s [{100*curr/dt:.1f}%]', end='', flush=True)

    print()


def add_stock_data(stock_data, tickers_to_remove, groups):
    print_debug('retrieving stock data...')
    start = time()

    count = 0
    total = len(groups)

    for ticker, dates in groups.items():
        start_date = dates.min()
        end_date = get_end_date(dates.max())

        yf.config.debug.hide_exceptions = False

        retries = 0
        while True:
            try:
                data = yf.Ticker(ticker).history(
                    start=start_date,
                    end=end_date,
                    auto_adjust=False,
                )
                stock_data[ticker] = data
                break

            except (
                yf.exceptions.YFPricesMissingError,
                yf.exceptions.YFTzMissingError,

            ):
                tickers_to_remove.add(ticker)
                break

            except HTTPError as e:
                if e.response is not None and e.response.status_code == 404:
                    tickers_to_remove.add(ticker)
                    break

                raise

            except yf.exceptions.YFRateLimitError:
                retries += 1

                if retries > 10:
                    tickers_to_remove.add(ticker)
                    break

                if retries == 1:
                    print('\nrate limit error, starting backoff strategy')

                print(f'attempt number {retries}')

                sleep_with_progress(7.5*2**retries + random() * 30)

            except Timeout:
                delay = 0.1 + 0.1*random()
                print(f'\nrequest timed out, retrying in {delay:.2f}s')
                sleep(delay)

        count += 1
        print(f'\rprogress: {count}/{total} [{count/total*100:.1f}%]',
              end='', flush=True)
        sleep(0.01)

    delta = time() - start

    print('\nfinished retrieving stock data in '
          f'{int(delta // 3600)} hours, '
          f'{int((delta % 3600) // 60)} '
          f'minutes, {delta % 60:.2f} seconds')


stock_data = {}
tickers_to_remove = set()

chunk_size = len(openinsider_data)
chunk_start = 0

while chunk_start < len(openinsider_data):
    try:
        print(
            f'retrieving data for slice {chunk_start}:{chunk_start+chunk_size}'
        )
        groups = (
            openinsider_data.iloc[chunk_start:chunk_start+chunk_size]
            .groupby('Ticker')[TRADE_DATE_COL]
            .unique()
        )
        add_stock_data(stock_data, tickers_to_remove, groups)

        chunk_start += chunk_size
        chunk_size = len(openinsider_data) - chunk_start

    except KeyError as e:
        if e.args[0] == 'chart':
            print('failed because chunk size was too big, reducing chunk size')
            chunk_size = chunk_size // 2
            if chunk_size < 1:
                chunk_size = 1
        else:
            raise


openinsider_data = (
    openinsider_data[~openinsider_data['Ticker'].isin(tickers_to_remove)]
)

print(
    'df length after removing '
    f'non-existent stock data: {len(openinsider_data)}'
)


# === Add the downloaded stock data to the dataset ===
def get_following_min_max_price(row):
    ticker = row['Ticker']
    close_prices = stock_data[ticker]['Close']
    date = pd.Timestamp(row[TRADE_DATE_COL], tz=close_prices.index.tz)

    date_index = close_prices.index.searchsorted(date)
    delta = (close_prices.index[date_index] - date).days
    start_date_index = date_index + 2 - min(delta, 2)

    if start_date_index >= len(close_prices):
        return pd.Series({
            'following_10_day_max': float('nan'),
            'following_10_day_min': float('nan')
        })

    base = close_prices.iloc[date_index]
    relevant_prices = close_prices.iloc[start_date_index:start_date_index+10]

    return pd.Series({
        'following_10_day_max': relevant_prices.max() / base,
        'following_10_day_min': relevant_prices.min() / base
    })


following_min_max = openinsider_data.apply(get_following_min_max_price, axis=1)
mask = following_min_max['following_10_day_max'].notna()

openinsider_data[
    ['following_10_day_max', 'following_10_day_min']
] = following_min_max
openinsider_data = openinsider_data[mask]

print(
    'df length after removing '
    f'insufficient stock data: {len(openinsider_data)}'
)

print(openinsider_data)

openinsider_data.to_csv('insider_trading_data.csv', sep='\x1F', index=False)

print_debug('processed stock data and wrote to disk')
