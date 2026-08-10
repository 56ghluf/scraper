import datetime
from os import listdir
import re
import requests
import traceback
import uuid
from pprint import pprint

import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.enums import (
    OrderSide, TimeInForce, OrderClass, OrderStatus
)
from alpaca.trading.requests import (
    LimitOrderRequest, TakeProfitRequest, StopLossRequest
)
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.common.exceptions import APIError

import data_loading_utils as dlus
from logging_utils import Logger

saved_state = dlus.load_json('curr_data/order_data.json')

index = saved_state['index']
ongoing_orders = saved_state['ongoing_orders']
orders = saved_state['orders']

model_names = [model_filename[:-7] for model_filename in listdir('models')]
new_data = pd.read_csv('curr_data/preds.csv', delimiter='\x1F').iloc[index:]

logger = Logger('update_orders')

if not dlus.in_prod():
    logger.add('*****DEVELOPPEMENT ENVIRONMENT*****\n')


def add_order(orders, ticker, take_stop_side, date):
    new_order = {'take_stop_side': take_stop_side, 'date': date}

    if ticker not in orders:
        logger.add(f'add_order [{ticker}]: {new_order}\n')
        orders[ticker] = new_order
        return

    if orders[ticker]['take_stop_side'][2] == 'sell':
        if take_stop_side[2] == 'buy':
            logger.add(
                f'add_order [{ticker}]: replaced {orders[ticker]} with {new_order}.\n')
            orders[ticker] = new_order
        elif orders[ticker]['take_stop_side'][0] > take_stop_side[0]:
            logger.add(
                f'add_order [{ticker}]: replaced {orders[ticker]} with {new_order}.\n')
            orders[ticker] = new_order
        return

    if take_stop_side[2] == 'sell':
        logger.add(
            f'add_order [{ticker}]: did not add {new_order} '
            f'(prefered {orders[ticker]}).\n')
        return

    logger.add(
        f'add_order [{ticker}]: replaced {orders[ticker]} with ')

    orders[ticker]['take_stop_side'][0] = max(
        orders[ticker]['take_stop_side'][0], take_stop_side[0]
    )
    orders[ticker]['take_stop_side'][1] = min(
        orders[ticker]['take_stop_side'][1], take_stop_side[1]
    )

    logger.add(f'{orders[ticker]}.\n')


def trade_too_old(date_str):
    if (
        datetime.date.today() -
        datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    ).days > 9:
        return True

    return False


logger.add('===Determine new orders from predictions===\n')
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
            logger.add(
                'fatal: there neither gain '
                f'nor loss in model_name: {model_name}\n'
            )

    if max_gain <= 0 and max_loss > 0:
        add_order(
            orders,
            row['Ticker'],
            [0.95, 1.05, 'sell'],
            row[dlus.TRADE_DATE_COL]
        )
        continue

    if max_gain <= max_loss:
        continue

    max_loss = max(max_loss, 0) + 5

    take_stop_side = [1+max_gain/100, 1-max_loss/100, 'buy']

    add_order(
        orders,
        row['Ticker'],
        take_stop_side,
        row[dlus.TRADE_DATE_COL]
    )


def ntfy(msg):
    if dlus.in_prod():
        requests.post(
            'https://ntfy.sh/bDoZa0LEbwHCE0br',
            data=msg
        )


def log_and_ntfy(msg):
    logger.add(msg)
    ntfy(msg)


def log_and_ntfy_err(err_msg):
    log_and_ntfy('***ERR_MSG***\n' + err_msg)


def normalize_price(price):
    if price < 1:
        return round(price, 4)
    return round(price, 2)


ALPACA_KEY = dlus.file_to_str('alpaca-key.key').strip()
ALPACA_SECRET = dlus.file_to_str('alpaca-secret.key').strip()
data_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)
trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET)


def get_latest_bar_data():
    bar_request_params = StockBarsRequest(
        symbol_or_symbols=orders.keys(),
        timeframe=TimeFrame.Day,
        start=datetime.datetime.strptime(
            min([order['date'] for order in orders.values()]), '%Y-%m-%d'
        ),
    )

    return data_client.get_stock_bars(bar_request_params).df


def rm_old_order(ticker):
    order = orders[ticker]

    if trade_too_old(order['date']):
        logger.add(f'Trade too old for {ticker}: {order["date"]}\n')
        del orders[ticker]
        return True

    return False


def rm_wrong_side_order(ticker):
    order = orders[ticker]

    if ticker in ongoing_orders:
        if ongoing_orders[ticker]['side'] != order['take_stop_side'][2]:
            logger.add(
                f'Order on opposite side for {ticker}. Current '
                + ongoing_orders[ticker]['side']
                + ' new ' + order['take_stop_side'][2] + '.\n'
            )
            return True

    return False


def rm_no_stock_data_order(ticker, bar_data):
    try:
        return bar_data.loc[ticker]
    except KeyError:
        log_and_ntfy(
            'Failed to get stock data '
            f'from alpaca for {ticker} (KeyError).\n'
        )
        del orders[ticker]
        return None


def get_bid_and_side(ticker, following_closes, take_profit, base):
    order = orders[ticker]

    if order['take_stop_side'][2] == 'sell':
        if (
            not pd.isna(following_closes.min()) and
            following_closes.min() <= take_profit
        ):
            logger.add(
                f'Went under take profit (side sell) for {ticker}.\n')
            del orders[ticker]
            return (-1, -1, True)

        return (0.998 * base, OrderSide.SELL, False)

    elif order['take_stop_side'][2] == 'buy':
        if (
            not pd.isna(following_closes.max()) and
            following_closes.max() >= take_profit
        ):
            logger.add(f'Went over take profit (side buy) for {ticker}.\n')
            del orders[ticker]
            return (-1, -1, True)

        return (1.002 * base, OrderSide.BUY, False)

    else:
        logger.add('get_bid_and_side: fatal, order is neither sell nor buy.\n')
        return (-1, -1, True)


def place_order(ticker, qty, side, bid, take_profit, stop_loss):
    remove_order = False
    order_id = ''

    if not dlus.in_prod():
        return (str(uuid.uuid4()), False, False)

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

        order_id = str(alpaca_order.id)

    except APIError as e:
        # Insufficient funds error
        if e.code == 40310000:
            log_and_ntfy(f'Insufficient funds, breaking ({e.message}).\n')
            return ('', False, True)

        elif e.code == 42210000:
            log_and_ntfy_err(
                f'Order was unprocessable ({e.message}):\n'
                f'symbol={ticker}, qty={qty}, side={side}, '
                f'time_in_force={TimeInForce.GTC}, '
                f'limit_price={normalize_price(bid)}, '
                f'order_class={OrderClass.BRACKET}, '
                f'take_profit/limit_price={normalize_price(take_profit)}, '
                f'stop_loss/stop_price={normalize_price(stop_loss)}\n'
            )
            remove_order = True

    except Exception:
        log_and_ntfy_err(
            'Unknown error occured when submitting the order:'
            f'{traceback.format_exc()}\n'
        )
        remove_order = True

    if remove_order:
        del orders[ticker]

    return (order_id, remove_order, False)


if len(orders) > 0:
    bar_data = get_latest_bar_data()

    MAX_ORDER_CAPITAL = 500

    logger.add('===Placing new orders on alpaca.===\n')

    for ticker in list(orders.keys()):
        order = orders[ticker]

        if rm_old_order(ticker):
            continue

        if rm_wrong_side_order(ticker):
            continue

        data = rm_no_stock_data_order(ticker, bar_data)
        if data is None:
            continue

        base_idx = data.index.searchsorted(order['date'])
        if base_idx > len(data):
            logger.add(f'No market data for {ticker}.\n')
            continue

        base = data.iloc[base_idx]['close']
        take_profit = base * order['take_stop_side'][0]
        stop_loss = base * order['take_stop_side'][1]

        following_closes = data.iloc[base_idx+1:]['close']

        bid, side, should_continue = get_bid_and_side(
            ticker, following_closes, take_profit, base
        )

        if should_continue:
            continue

        qty = int(MAX_ORDER_CAPITAL / bid)

        if qty == 0:
            log_and_ntfy(
                f'Bid qty was 0 (order capital too small) for {ticker}.\n'
            )
            del orders[ticker]
            continue

        order_id, should_continue, should_break = place_order(
            ticker, qty, side, bid, take_profit, stop_loss
        )

        if should_break:
            break

        if should_continue:
            continue

        if ticker not in ongoing_orders:
            ongoing_orders[ticker] = {
                'info': [],
                'side': order['take_stop_side'][2]
            }

        order_info = [order['date'], take_profit, order_id]
        ongoing_orders[ticker]['info'].append(order_info)

        del orders[ticker]
        logger.add(
            f'Completed order for {ticker} (limit at {bid}): {order_info}.\n')
else:
    logger.add('No new orders.\n')


def cancel_order(order_info):
    if not dlus.in_prod():
        return

        trading_client.cancel_order_by_id(uuid.UUID(order_info[2]))


logger.add('===Removing no longer necessary orders===\n')
market_open = trading_client.get_clock().is_open

if not market_open:
    logger.add('Market is closed.\n')

for ticker in list(ongoing_orders.keys()):
    remaining_info = []

    bid_price = None

    for order_info in ongoing_orders[ticker]['info']:
        if dlus.in_prod():
            updated_order = trading_client.get_order_by_id(
                uuid.UUID(order_info[2])
            )

            if updated_order.status == OrderStatus.FILLED:
                logger.add(f'{order_info[2]} filled for {ticker}.\n')
                continue

        if trade_too_old(order_info[0]):
            logger.add(f'{order_info[2]} too old for {ticker}.\n')
            cancel_order(order_info)
            continue

        if not market_open:
            remaining_info.append(order_info)
            continue

        if bid_price is None:
            bid_price = data_client.get_stock_latest_quote(
                StockLatestQuoteRequest(symbol_or_symbols=ticker)
            )[ticker].bid_price

        if bid_price >= order_info[1]:
            logger.add(
                f'{order_info[2]} bid price ({bid_price}) went '
                f'over take profit ({order_info[1]}) for {ticker}.\n'
            )
            cancel_order(order_info)
            continue

        remaining_info.append(order_info)

    if len(remaining_info) == 0:
        del ongoing_orders[ticker]
    else:
        ongoing_orders[ticker]['info'] = remaining_info

if dlus.in_prod():
    dlus.write_json(
        {'index': index, 'ongoing_orders': ongoing_orders, 'orders': orders},
        'curr_data/order_data.json'
    )
else:
    print('index:', index)
    print('>>>>>>>>>>ongoing_orders:')
    pprint(ongoing_orders)
    print('\n\n>>>>>>>>>>orders:')
    pprint(orders)
