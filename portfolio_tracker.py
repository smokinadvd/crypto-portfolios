import requests
import schedule
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from openpyxl import Workbook

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

def get_alpha_vantage_index_price(symbol):
    params = {
        'function': 'TIME_SERIES_DAILY',
        'symbol': symbol,
        'apikey': alpha_vantage_api_key
    }
    response = requests.get(alpha_vantage_url, params=params)
    if response.status_code == 200:
        data = response.json()
        try:
            latest_date = max(data['Time Series (Daily)'].keys())
            return float(data['Time Series (Daily)'][latest_date]['4. close'])
        except KeyError:
            logging.error(f"Unexpected data format for {symbol}: {data}")
            return None
    else:
        logging.error(f"Error retrieving data for {symbol}: {response.json()}")
        return None

def save_portfolio(workbook, portfolio):
    sheet_name = f"Portfolio {portfolio['creation_date'].strftime('%Y-%m-%d')}"
    sheet = workbook.create_sheet(title=sheet_name)

    # Add headers
    headers = ['Coin Name', 'Symbol', 'ID', 'Initial Price', '24h Change', '7d Change', 'Market Cap']
    headers.extend([f'Month {i+1} Price' for i in range(12)])
    sheet.append(headers)

    # Add coin data
    for coin_data in portfolio['coins'].values():
        coin = coin_data['coin']
        row = [
            coin.name,
            coin.symbol,
            coin.id,
            coin.price,
            coin.change_24h,
            coin.change_7d,
            coin.market_cap
        ]
        row.extend(coin_data.get('monthly_prices', []))
        sheet.append(row)

    # Add index data at the bottom
    sheet.append([])
    index_prices = portfolio.get('index_prices', {})
    for index_name, prices in index_prices.items():
        row = [index_name, '', '', prices[0]]  # Initial price
        row.extend(prices[1:])  # Monthly prices
        sheet.append(row)

def create_and_track_portfolios():
    min_market_cap = 100000
    portfolio_size = 150000
    workbook = Workbook()

    latest_meme_coins = get_latest_meme_coins(min_market_cap)
    num_coins = len(latest_meme_coins)
    if num_coins < 100:
        logging.error("Not enough coins to create a full portfolio. Skipping this creation.")
        return

    investment_per_coin = portfolio_size / num_coins

    portfolio = {
        'creation_date': datetime.now(),
        'coins': {coin.id: {'coin': coin, 'investment': investment_per_coin, 'monthly_prices': []} for coin in latest_meme_coins},
        'index_prices': {
            'BTC': [get_alpha_vantage_index_price('BTC-USD')],
            'SOL': [get_alpha_vantage_index_price('SOL-USD')],
            'NASDAQ': [get_alpha_vantage_index_price('^IXIC')],
        }
    }

    save_portfolio(workbook, portfolio)
    portfolio_path = 'portfolios.xlsx'
    workbook.save(portfolio_path)

    # Schedule tracking of the portfolio
    for i in range(1, 12):  # Track monthly for 12 months
        schedule.every(i).months.do(track_portfolio_performance, portfolio=portfolio, workbook=workbook, month=i)

def track_portfolio_performance(portfolio, workbook, month):
    coin_ids = list(portfolio['coins'].keys())
    params = {
        'id': ','.join(map(str, coin_ids)),
        'convert': 'USD'
    }
    response = requests.get(url_quotes, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()['data']
        for coin_id, coin_data in portfolio['coins'].items():
            coin_data['monthly_prices'].append(data[str(coin_id)]['quote']['USD']['price'])
    
    # Update index prices
    portfolio['index_prices']['BTC'].append(get_alpha_vantage_index_price('BTC-USD'))
    portfolio['index_prices']['SOL'].append(get_alpha_vantage_index_price('SOL-USD'))
    portfolio['index_prices']['NASDAQ'].append(get_alpha_vantage_index_price('^IXIC'))

    save_portfolio(workbook, portfolio)
    portfolio_path = 'portfolios.xlsx'
    workbook.save(portfolio_path)

# Set up scheduling for portfolio creation and tracking
schedule.every().day.do(create_and_track_portfolios)

# Run the scheduled jobs
while True:
    schedule.run_pending()
    time.sleep(1)
