from os import listdir

import pandas as pd
from joblib import load

import data_loading_utils as dlus


try:
    new_data = pd.read_csv('curr_data/raw_data.csv',
                           delimiter='\x1F',
                           dtype={'X': 'string',
                                  dlus.FILING_DATE_COL: 'string',
                                  dlus.TRADE_DATE_COL: 'string',
                                  'Ticker': 'string',
                                  'Title': 'string',
                                  dlus.TRADE_TYPE_COL: 'string'},
                           converters={'Price': dlus.price_to_float,
                                       'Qty': dlus.str_with_commas_to_float,
                                       'Owned': dlus.str_with_commas_to_float,
                                       dlus.OWN_COL: dlus.own_to_float,
                                       'Value': dlus.price_to_float})
except pd.errors.EmptyDataError:
    print('no openinsider data available, quitting')
    exit()

new_data.dropna(subset=['Ticker'])
new_data['Ticker'] = new_data['Ticker'].str.strip()

new_data.drop(columns=new_data.columns[17], inplace=True)
new_data.drop(columns=[
    dlus.FILING_DATE_COL,
    dlus.COMPANY_NAME_COL,
    dlus.INSIDER_NAME_COL,
    'Title',
    '1d', '1w', '1m', '6m'
], inplace=True)

new_data['X'] = new_data['X'].fillna('missing')

# make the dates useable (base 31 encoding)
new_data['numeric_trade_dates'] = (
    new_data[dlus.TRADE_DATE_COL].apply(dlus.date_str_to_numeric)
)

try:
    old_preds = pd.read_csv('curr_data/preds.csv', delimiter='\x1F')

    cols = new_data.columns

    new_data = (
        new_data.merge(old_preds[cols], how='left', indicator=True)
        .query('_merge == \'left_only\'')
        .drop(columns='_merge')
    )

except FileNotFoundError:
    old_preds = None

if not new_data.empty:
    for model_filename in listdir('models')[:2]:
        model = load(f'models/{model_filename}')
        preds = model.predict(new_data.drop(columns=dlus.TRADE_DATE_COL))
        new_data[model_filename[:-7]] = model.predict(new_data)

(
    pd.concat([old_preds, new_data], ignore_index=True)
).to_csv('curr_data/preds.csv', sep='\x1F', index=False)
