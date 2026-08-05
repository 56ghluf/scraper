import datetime
from os import listdir
import re
import requests
import traceback
import uuid

import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, OrderStatus
from alpaca.trading.requests import (
    LimitOrderRequest, TakeProfitRequest, StopLossRequest
)
from alpaca.data.requests import StockLatestQuoteRequest

from alpaca.common.exceptions import APIError

import data_loading_utils as dlus

saved_state = dlus.load_json('curr_data/order_data.json')

index = saved_state['index']
ongoing_orders = saved_state['ongoing_orders']
orders = saved_state['orders']


def add_order(orders, ticker, take_stop_side, date):
    new_order = {'take_stop_side': take_stop_side, 'date': date}

    if ticker not in orders:
        orders[ticker] = new_order
        return

    if orders[ticker]['take_stop_side'][2] == 'sell':
        if take_stop_side[2] == 'buy':
            orders[ticker] = new_order
        elif orders[ticker]['take_stop_side'][0] > take_stop_side[0]:
            orders[ticker] = new_order
        return

    if take_stop_side[2] == 'sell':
        return

    orders[ticker]['take_stop_side'][0] = max(
        orders[ticker]['take_stop_side'][0], take_stop_side[0]
    )

    orders[ticker]['take_stop_side'][1] = min(
        orders[ticker]['take_stop_side'][1], take_stop_side[1]
    )


model_names = [model_filename[:-7] for model_filename in listdir('models')]
new_data = pd.read_csv('curr_data/preds.csv', delimiter='\x1F').iloc[index:]


def trade_too_old(date_str):
    if (
        datetime.date.today() -
        datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    ).days > 9:
        return True

    return False


for row in new_data.to_dict('records'):
    index += 1
    if trade_too_old(row[dlus.TRADE_DATE_COL]):
        continue

    max_gain = -1
    max_loss = -1

    for model_name in model_names:
        if not row[model_name] or pd.isna(row[model_name]):
            continue

        threshold = int(re.search(r'thld(\d+)', model_name).group(1))

        if 'gain' in model_name and threshold > max_gain:
            max_gain = threshold
        elif 'loss' in model_name and threshold > max_loss:
            max_loss = threshold
        elif not ('gain' in model_name or 'loss' in model_name):
            print(
                'fatal: there neither gain '
                f'nor loss in model_name: {model_name}'
            )

    if max_gain <= 0 and max_loss > 0:
        add_order(
            orders,
            row['Ticker'],
            [0.95, 1.05, 'sell'],
            row[dlus.TRADE_DATE_COL]
        )
        continue

    if max_gain <= 0:
        continue

    max_loss = max(max_loss, 0) + 5

    add_order(
        orders,
        row['Ticker'],
        [1+max_gain/100, 1-max_loss/100, 'buy'],
        row[dlus.TRADE_DATE_COL]
    )

ALPACA_KEY = dlus.file_to_str('alpaca-key.key').strip()
ALPACA_SECRET = dlus.file_to_str('alpaca-secret.key').strip()

data_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

bar_request_params = StockBarsRequest(
    symbol_or_symbols=orders.keys(),
    timeframe=TimeFrame.Day,
    start=datetime.datetime.strptime(
        min([order['date'] for order in orders.values()]), '%Y-%m-%d'
    ),
)

bar_data = data_client.get_stock_bars(bar_request_params).df

trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET)

MAX_ORDER_CAPITAL = 5000


def print_and_send_error_notification(err_msg):
    err_msg = '=== ERR_MSG ===\n' + err_msg
    print(err_msg)
    requests.post(
        'https://ntfy.sh/bDoZa0LEbwHCE0br',
        data=err_msg
    )


def normalize_price(price):
    if price < 1:
        return round(price, 4)
    return round(price, 2)


for ticker in list(orders.keys()):
    order = orders[ticker]

    if trade_too_old(order['date']):
        del orders[ticker]
        continue

    if ticker in ongoing_orders:
        if ongoing_orders[ticker]['side'] != order['take_stop_side'][2]:
            continue

    try:
        data = bar_data.loc[ticker]
    except KeyError:
        print_and_send_error_notification(
            f'failed to get stock data from alpaca for {ticker}:'
            ' got KeyError'
        )
        del orders[ticker]
        continue

    base_idx = data.index.searchsorted(order['date'])
    if base_idx > len(data):
        continue

    base = data.iloc[base_idx]['close']
    take_profit = base * order['take_stop_side'][0]
    stop_loss = base * order['take_stop_side'][1]

    following_closes = data.iloc[base_idx+1:]['close']

    if order['take_stop_side'][2] == 'sell':
        if (
            not pd.isna(following_closes.min()) and
            following_closes.min() <= take_profit
        ):
            del orders[ticker]
            continue

        bid = 0.99 * base
        side = OrderSide.SELL
    else:
        if (
            not pd.isna(following_closes.max()) and
            following_closes.max() >= take_profit
        ):
            del orders[ticker]
            continue

        bid = 1.01 * base
        side = OrderSide.BUY

    qty = int(MAX_ORDER_CAPITAL / bid)

    if qty == 0:
        orders[ticker]
        continue

    try:
        alpaca_order = trading_client.submit_order(
            LimitOrderRequest(
                symbol=ticker,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.GTC,
                limit_price=normalize_price(bid),
                order_class=OrderClass.BRACKET,
                take_profit=TakeProfitRequest(
                    limit_price=normalize_price(take_profit)
                ),
                stop_loss=StopLossRequest(
                    stop_price=normalize_price(stop_loss)
                )
            )
        )
    except APIError as e:
        # Insufficient funds error
        if e.code == 40310000:
            break
        else:
            print_and_send_error_notification(
                'something went wrong when submitting the order: '
                f'{traceback.format_exc()}'
            )
            del orders[ticker]
            continue

    except Exception:
        print_and_send_error_notification(
            'something went wrong when submitting the order: '
            f'{traceback.format_exc()}'
        )
        del orders[ticker]
        continue

    if ticker not in ongoing_orders:
        ongoing_orders[ticker] = {'info': [], side: order['take_stop_side'][2]}

    ongoing_orders[ticker]['info'].append([
        order['date'], take_profit, str(alpaca_order.id)
    ])

    del orders[ticker]

# for ticker, order in ongoing_orders.items():
    # remaining_info = []

    # for order_info in order['info']:
        # updated_order = trading_client.get_order_by_id(
            # uuid.UUID(order_info[2])
        # )

        # if updated_order.status == OrderStatus.FILLED:
            # continue

        # if trade_too_old(order_info[0]):
            # trading_client.cancel_order_by_id(uuid.UUID(order_info[2]))
            # continue

        # if not trading_client.clock().is_open:
            # remaining_info.append[order_info]
            # continue

        # latest_quote = data_client.get_stock_lateset_quote(
            # StockLatestQuoteRequest(symbol_or_symbols='ticker')
        # )


dlus.write_json(
    {'index': index, 'ongoing_orders': ongoing_orders, 'orders': orders},
    'curr_data/order_data.json'
)
