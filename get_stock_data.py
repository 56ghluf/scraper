from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

def str_to_float(x):
    if (x == ''):
        return float('nan')
    if (x == '>999'):
        return 1000
    try:
        return float(x)
    except (TypeError, ValueError):
        print(f'FATAL -- str_to_float: could not convert {x} to float')

openinsider_data = pd.read_csv('openinsider_data.csv', delimiter='\x1F', converters={'1w': str_to_float, '1m': str_to_float, '6m': str_to_float})

# ticker = 'JEF'
# start_date = '2026-07-14'
# end_date = '2026-07-17'

# stock_data = yf.download(ticker, start=start_date, end=end_date, progress=True)


def get_following_min_max_price(row):
    # very important to use THIS string
    # it has a non-breaking space (U+00A0)
    # why does openinsider.com use one? I have no idea
    trade_date_col = 'Trade Date'
    start_date = row[trade_date_col]
    end_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = (end_date + timedelta(10)).strftime('%Y-%m-%d')

    ticker = row['Ticker']
    if (type(ticker) == float):
        print(row)
    elif (len(ticker) > 5):
        print(ticker, ' ', [f'U+{ord(c):04X}' for c in ticker])

    # print(f'{start_date} {end_date} {ticker}')

    return pd.Series({'following_10_day_max': 0, 'following_10_day_min': 0})


# openinsider_data[['following_10_day_max', 'following_10_day_min']] = openinsider_data.apply(get_following_min_max_price, axis=1)

# for el in openinsider_data.head(500)['6m']:
    # print(el)

