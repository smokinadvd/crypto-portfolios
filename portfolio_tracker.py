import requests
import pandas as pd
import openpyxl
from datetime import datetime, timedelta
import logging
import os
import time

# Setup logging
logging.basicConfig(level=logging.INFO)

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

def create_and_track_portfolios():
    min_market_cap = 100000
    portfolio_size = 150000

    # Load or create Excel file
    portfolio_path = 'portfolios.xlsx'
    if os.path.exists(portfolio_path):
        workbook = pd.ExcelFile(portfolio_path)
    else:
        workbook = None

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

    # Track and save the portfolio
    save_portfolio(workbook, portfolio)

    # Schedule monthly tracking for 12 months
    for month in range(1, 13):
        time.sleep(2)  # small sleep to avoid hitting rate limits
        track_portfolio_performance(portfolio, num_coins, month)

def save_portfolio(workbook, portfolio):
    df = pd.DataFrame({
        'ID': [coin.id for coin in portfolio['coins'].values()],
        'Symbol': [coin['coin'].symbol for coin in portfolio['coins'].values()],
        'Name': [coin['coin'].name for coin in portfolio['coins'].values()],
        'Initial Price': [coin['coin'].price for coin in portfolio['coins'].values()],
        'Market Cap': [coin['coin'].market_cap for coin in portfolio['coins'].values()],
        '24h Change': [coin['coin'].change_24h for coin in portfolio['coins'].values()],
        '7d Change': [coin['coin'].change_7d for coin in portfolio['coins'].values()],
        'Investment': [coin['investment'] for coin in portfolio['coins'].values()],
    })

    sheet_name = f"Portfolio {portfolio['creation_date'].strftime('%Y-%m-%d')}"
    if workbook:
        with pd.ExcelWriter(portfolio_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        with pd.ExcelWriter(portfolio_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    logging.info(f"Portfolio saved: {sheet_name}")

def track_portfolio_performance(portfolio, num_coins, month):
    # Advance the date by the given number of months
    track_date = portfolio['creation_date'] + timedelta(days=30 * month)
    if datetime.now() < track_date:
        return

    coin_ids = list(portfolio['coins'].keys())
    updated_coin_data = get_coin_data_by_ids(coin_ids)

    total_return = 0
    df = pd.DataFrame()
    for coin_id in coin_ids:
        initial_coin = portfolio['coins'][coin_id]['coin']
        initial_price = initial_coin.price
        updated_price = updated_coin_data[str(coin_id)]['quote']['USD']['price']
        investment = portfolio['coins'][coin_id]['investment']
        return_percentage = ((updated_price - initial_price) / initial_price) * 100
        total_return += return_percentage
        df = df.append({
            'Month': month,
            'Symbol': initial_coin.symbol,
            'Name': initial_coin.name,
            'Initial Price': initial_price,
            'Updated Price': updated_price,
            'Return (%)': return_percentage
        }, ignore_index=True)

    average_return = total_return / num_coins
    logging.info(f"Total Return after {month} months: {total_return:.2f}% | Average Return: {average_return:.2f}%")

    # Save the monthly tracking data
    portfolio_path = 'portfolios.xlsx'
    sheet_name = f"Portfolio {portfolio['creation_date'].strftime('%Y-%m-%d')}_Month_{month}"
    with pd.ExcelWriter(portfolio_path, engine='openpyxl', mode='a') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

# Main Execution Logic
portfolios = []

# Create initial portfolio
create_and_track_portfolios()

# Ensure new portfolios are created every 24 hours and tracked monthly
while len(portfolios) < 365:
    time.sleep(86400)  # Sleep for 24 hours
    create_and_track_portfolios()
