import requests
import schedule
import time
from datetime import datetime, timedelta
import logging
import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

# Setup logging
logging.basicConfig(level=logging.INFO)

# Define the API endpoint and the provided API key
api_key = "your_coinmarketcap_api_key"
url_latest = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
url_quotes = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': api_key,
}

class Coin:
    def __init__(self, id, symbol, name, price, change_24h, change_7d, market_cap, date_added, timestamp):
        self.id = id
        self.symbol = symbol
        self.name = name
        self.price = price if price is not None else 0.0
        self.change_24h = change_24h if change_24h is not None else 0.0
        self.change_7d = change_7d if change_7d is not None else 0.0
        self.market_cap = market_cap if market_cap is not None else 0.0
        self.date_added = date_added
        self.timestamp = timestamp

    def __str__(self):
        return f"{self.symbol} | {self.name} | ${self.price:.8f} | {self.change_24h:.2f}% | {self.change_7d:.2f}% | ${self.market_cap:.2f} | {self.timestamp}"

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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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
                    coin_instance = Coin(id, symbol, name, price, change_24h, change_7d, market_cap, date_added, timestamp)
                    filtered_meme_coins.append(coin_instance)

                    if len(filtered_meme_coins) == 100:
                        break
    else:
        logging.error(f"Error: {response.json()['status']['error_message']}")
    
    logging.info(f"Number of coins fetched from CoinMarketCap: {len(filtered_meme_coins)}")
    return filtered_meme_coins

def get_coin_data_by_ids(coin_ids):
    params = {
        'id': ','.join(map(str, coin_ids)),
        'convert': 'USD'
    }
    response = requests.get(url_quotes, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()['data']
    else:
        logging.error(f"Error: {response.json()['status']['error_message']}")
        return {}

def save_portfolio(workbook, portfolio):
    sheet_name = portfolio['creation_date'].strftime('%Y-%m-%d')
    if sheet_name not in workbook.sheetnames:
        workbook.create_sheet(title=sheet_name)
    sheet = workbook[sheet_name]

    data = {
        'ID': [coin['coin'].id for coin in portfolio['coins'].values()],
        'Symbol': [coin['coin'].symbol for coin in portfolio['coins'].values()],
        'Name': [coin['coin'].name for coin in portfolio['coins'].values()],
        'Price': [coin['coin'].price for coin in portfolio['coins'].values()],
        '24h Change': [coin['coin'].change_24h for coin in portfolio['coins'].values()],
        '7d Change': [coin['coin'].change_7d for coin in portfolio['coins'].values()],
        'Market Cap': [coin['coin'].market_cap for coin in portfolio['coins'].values()],
        'Investment': [coin['investment'] for coin in portfolio['coins'].values()],
    }

    df = pd.DataFrame(data)
    for r in dataframe_to_rows(df, index=False, header=True):
        sheet.append(r)

    workbook.save('portfolios.xlsx')

def create_and_track_portfolios():
    min_market_cap = 100000
    portfolio_size = 150000

    latest_meme_coins = get_latest_meme_coins(min_market_cap)
    num_coins = len(latest_meme_coins)
    if num_coins < 100:
        logging.error("Not enough coins to create a full portfolio. Skipping this creation.")
        return

    investment_per_coin = portfolio_size / num_coins

    portfolio = {
        'creation_date': datetime.now(),
        'coins': {coin.id: {'coin': coin, 'investment': investment_per_coin} for coin in latest_meme_coins},
        'returns': []
    }

    try:
        workbook = load_workbook('portfolios.xlsx')
    except FileNotFoundError:
        workbook = Workbook()
        workbook.remove(workbook.active)

    save_portfolio(workbook, portfolio)

    schedule.every(30).days.do(track_portfolio_performance, portfolio=portfolio, num_coins=num_coins)

def track_portfolio_performance(portfolio, num_coins):
    coin_ids = list(portfolio['coins'].keys())
    updated_coin_data = get_coin_data_by_ids(coin_ids)

    total_return = 0
    for coin_id in coin_ids:
        initial_coin = portfolio['coins'][coin_id]['coin']
        initial_price = initial_coin.price
        updated_price = updated_coin_data[str(coin_id)]['quote']['USD']['price']
        investment = portfolio['coins'][coin_id]['investment']
        return_percentage = ((updated_price - initial_price) / initial_price) * 100
        total_return += return_percentage
        logging.info(f"{initial_coin.symbol} | Initial Price: ${initial_price:.8f} | Updated Price: ${updated_price:.8f} | Return: {return_percentage:.2f}%")

    average_return = total_return / num_coins
    logging.info(f"Total Return: {total_return:.2f}% | Average Return: {average_return:.2f}%")

# Schedule to create a new portfolio every day
schedule.every().day.at("00:00").do(create_and_track_portfolios)

while True:
    schedule.run_pending()
    time.sleep(1)
