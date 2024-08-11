import requests
import pandas as pd
import schedule
import time
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Define the API endpoint and the provided API key
api_key = "8e58e4ac-182a-4c41-ac41-6f7032cfd47c"
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
        'limit': '5000',  # Adjust as needed
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

def save_portfolio_to_excel(portfolio_data, file_path):
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        for portfolio_name, data in portfolio_data.items():
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name=portfolio_name)

        # Ensure at least one sheet is visible
        if not writer.book.worksheets:
            writer.book.create_sheet(title='Sheet1')

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
    portfolios.append(portfolio)

    schedule_time = portfolio['creation_date'] + timedelta(minutes=30)
    schedule.every().month.at(schedule_time.strftime('%Y-%m-%d %H:%M')).do(track_portfolio_performance, portfolio=portfolio, num_coins=num_coins)

    if len(portfolios) >= 20:
        return schedule.CancelJob

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

    # Save data to Excel
    portfolio_path = 'portfolios.xlsx'
    portfolio_data = {f"Portfolio_{portfolio['creation_date'].strftime('%Y-%m-%d')}": portfolio['coins']}
    save_portfolio_to_excel(portfolio_data, portfolio_path)

portfolios = []
schedule.every().month.do(create_and_track_portfolios)

start_time = datetime.now()
while len(portfolios) < 20 or (datetime.now() - start_time).total_seconds() < 86400:
    schedule.run_pending()
    time.sleep(1)

for idx, portfolio in enumerate(portfolios):
    logging.info(f"Portfolio {idx + 1} created at {portfolio['creation_date']}")
    for coin_id, details in portfolio['coins'].items():
        logging.info(f"{details['coin'].symbol}: Invested: ${details['investment']:.2f} | Current Price: ${details['coin'].price:.8f}")

time.sleep(86400)
