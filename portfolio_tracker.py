import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
from openpyxl import Workbook, load_workbook
import os

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Define the API endpoints and the provided API keys
api_key = "8e58e4ac-182a-4c41-ac41-6f7032cfd47c"
url_latest = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
url_quotes = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': api_key,
}

alpha_vantage_api_key = "BVGR4LWJ5G0F11HD"
alpha_vantage_url = "https://www.alphavantage.co/query"

portfolio_file = "portfolios.xlsx"

class Coin:
    def __init__(self, id, symbol, name, price, change_24h, change_7d, market_cap, date_added):
        self.id = id
        self.symbol = symbol
        self.name = name
        self.price = price if price is not None else 0.0
        self.change_24h = change_24h if change_24h is not None else 0.0
        self.change_7d = change_7d if change_7d is not None else 0.0
        self.market_cap = market_cap if market_cap is not None else 0.0
        self.date_added = date_added

    def __str__(self):
        return f"{self.symbol} | {self.name} | ${self.price:.8f} | {self.change_24h:.2f}% | {self.change_7d:.2f}% | ${self.market_cap:.2f}"

def get_latest_meme_coins(min_market_cap=100000):
    params = {
        'start': '1',
        'limit': '5000',
        'sort': 'date_added',
        'sort_dir': 'desc',
        'convert': 'USD'
    }
    response = requests.get(url_latest, headers=headers, params=params)
    filtered_meme_coins = []
    
    if response.status_code == 200:
        data = response.json()
        for coin in data['data']:
            tags = coin.get('tags', [])
            if 'memes' in tags:
                id = coin['id']
                symbol = coin['symbol']
                name = coin['name']
                quote = coin['quote']['USD']
                price = quote.get('price', 0)
                change_24h = quote.get('percent_change_24h', 0)
                change_7d = quote.get('percent_change_7d', 0)
                market_cap = quote.get('market_cap', 0)
                if market_cap >= min_market_cap:
                    date_added = coin.get('date_added', '1970-01-01T00:00:00Z')
                    coin_instance = Coin(id, symbol, name, price, change_24h, change_7d, market_cap, date_added)
                    filtered_meme_coins.append(coin_instance)

                    if len(filtered_meme_coins) == 100:
                        break
    else:
        logging.error(f"Error: {response.json()['status']['error_message']}")
    
    logging.info(f"Number of coins fetched from CoinMarketCap: {len(filtered_meme_coins)}")
    return filtered_meme_coins

def get_alpha_vantage_price(symbol):
    params = {
        'function': 'TIME_SERIES_DAILY',
        'symbol': symbol,
        'apikey': alpha_vantage_api_key
    }
    response = requests.get(alpha_vantage_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if "Time Series (Daily)" in data:
            latest_date = list(data["Time Series (Daily)"].keys())[0]
            return data["Time Series (Daily)"][latest_date]["4. close"]
        else:
            logging.error(f"Error: No data found for {symbol}")
            return None
    else:
        logging.error(f"Error: {response.json()}")
        return None

def load_portfolio_data():
    if not os.path.exists(portfolio_file):
        workbook = Workbook()
        workbook.save(portfolio_file)
        return {}

    workbook = load_workbook(portfolio_file)
    sheet = workbook.active
    portfolio_data = {}

    for i, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        if i == 1:
            continue  # Skip header row
        portfolio_data[row[0]] = {
            'creation_date': row[1],
            'coin_ids': row[2],
            'index_prices': {
                'BTC': row[3],
                'SOL': row[4]
            },
            'monthly_prices': row[5:]
        }

    return portfolio_data

def save_portfolio_data(portfolio_data):
    workbook = Workbook()
    sheet = workbook.active
    headers = ['Portfolio', 'Creation Date', 'Coin IDs', 'BTC Price', 'SOL Price', 'Monthly Prices']
    sheet.append(headers)

    for portfolio_name, data in portfolio_data.items():
        row = [
            portfolio_name,
            data['creation_date'],
            data['coin_ids'],
            data['index_prices']['BTC'],
            data['index_prices']['SOL'],
            *data['monthly_prices']
        ]
        sheet.append(row)

    workbook.save(portfolio_file)

def create_new_portfolio():
    portfolio_data = load_portfolio_data()
    portfolio_count = len(portfolio_data) + 1
    portfolio_name = f"Portfolio_{portfolio_count}"
    
    latest_meme_coins = get_latest_meme_coins()
    coin_ids = [coin.id for coin in latest_meme_coins]
    index_prices = {
        'BTC': get_alpha_vantage_price('BTC-USD'),
        'SOL': get_alpha_vantage_price('SOL-USD')
    }

    portfolio_data[portfolio_name] = {
        'creation_date': datetime.now().strftime("%Y-%m-%d"),
        'coin_ids': coin_ids,
        'index_prices': index_prices,
        'monthly_prices': []
    }

    save_portfolio_data(portfolio_data)

def update_portfolios():
    portfolio_data = load_portfolio_data()
    today = datetime.now()

    for portfolio_name, data in portfolio_data.items():
        creation_date = datetime.strptime(data['creation_date'], "%Y-%m-%d")
        if today >= creation_date + timedelta(days=30 * len(data['monthly_prices'])):
            # Update the portfolio
            new_prices = {
                'BTC': get_alpha_vantage_price('BTC-USD'),
                'SOL': get_alpha_vantage_price('SOL-USD')
            }
            data['monthly_prices'].append(new_prices)
    
    save_portfolio_data(portfolio_data)

if __name__ == "__main__":
    create_new_portfolio()
    update_portfolios()
