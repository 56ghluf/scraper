from datetime import date

# annoying column name constants
FILING_DATE_COL = 'Filing\xA0Date'
TRADE_DATE_COL = 'Trade\xA0Date'
COMPANY_NAME_COL = 'Company\xA0Name'
INSIDER_NAME_COL = 'Insider\xA0Name'
TRADE_TYPE_COL = 'Trade\xA0Type\xA0\xA0'
OWN_COL = chr(916) + 'Own'


# some custom converters
def custom_str_to_float(x):
    if x == '':
        return float('nan')
    if x == '>999':
        return 1000
    try:
        return float(x)
    except (TypeError, ValueError) as e:
        print(f'custom_str_to_float: could not convert {x} to float')
        raise e


def str_with_commas_to_float(x):
    return float(x.replace(',', '').strip())


def price_to_float(x):
    return str_with_commas_to_float(x.replace('$', ''))


def own_to_float(x):
    global count
    if x == 'New':
        return 2000

    if '>999%' == x:
        return 1500

    return str_with_commas_to_float(x.replace('%', ''))


# trade dates to numeric value
def date_str_to_numeric(date_str):
    return 31*(int(date_str[5:7])-1) + int(date_str[8:10])


def date_str_delta(str1, str2):
    return (date.fromisoformat(str2[:10]) - date.fromisoformat(str1[:10])).days
