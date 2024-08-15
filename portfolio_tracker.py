import requests
import pandas as pd
import openpyxl
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Define the CoinMarketCap API endpoint and your API key
coinmarketcap_api_key = "8e58e4ac-182a-4c41-ac41-6f7032cfd47c"
coinmarketcap_url_latest = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
coinmarketcap_headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': coinmarketcap_api_key,
}

# Define the Finnhub API endpoint and your API key
finnhub_api_key = "cquq339r01qvea0bvp60cquq339r01qvea0bvp6g"
finnhub_base_url = "https://finnhub.io/api/v1"

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
    response = requests.get(coinmarketcap_url_latest, headers=coinmarketcap_headers, params=params)
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

def get_index_price(symbol, date):
    url = f"{finnhub_base_url}/quote"
    params = {
        'symbol': symbol,
        'token': finnhub_api_key
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data['c']  # Current price
    else:
        logging.error(f"Error fetching data for index {symbol}: {response.json()['error']}")
        return None

def save_portfolio(workbook, portfolio):
    sheet_name = f"Portfolio_{portfolio['creation_date'].strftime('%Y-%m-%d')}"
    worksheet = workbook.create_sheet(sheet_name)

    worksheet.append([
        'ID', 'Symbol', 'Name', 'Price', '24h Change (%)', '7d Change (%)', 'Market Cap', 'Creation Date', 'Timestamp',
        'BTC Price', 'SOL Price', 'S&P 500 Price', 'Dow Jones Price', 'NASDAQ Composite Price'
    ])

    btc_price = get_index_price("BINANCE:BTCUSDT", portfolio['creation_date'])
    sol_price = get_index_price("BINANCE:SOLUSDT", portfolio['creation_date'])
    sp500_price = get_index_price("^GSPC", portfolio['creation_date'])
    dow_price = get_index_price("^DJI", portfolio['creation_date'])
    nasdaq_price = get_index_price("^IXIC", portfolio['creation_date'])

    for coin in portfolio['coins'].values():
        worksheet.append([
            coin.id, coin.symbol, coin.name, coin.price, coin.change_24h, coin.change_7d, coin.market_cap, coin.date_added, coin.timestamp,
            btc_price, sol_price, sp500_price, dow_price, nasdaq_price
        ])

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
        'coins': {coin.id: coin for coin in latest_meme_coins},
        'returns': []
    }
    portfolios.append(portfolio)

    workbook = openpyxl.Workbook()
    portfolio_path = 'portfolios.xlsx'
    save_portfolio(workbook, portfolio)

    schedule_time = portfolio['creation_date'] + timedelta(minutes=30)
    schedule.every().day.at(schedule_time.strftime('%H:%M')).do(track_portfolio_performance, portfolio=portfolio, num_coins=num_coins, workbook=workbook, portfolio_path=portfolio_path)

    workbook.save(portfolio_path)
    workbook.close()

    if len(portfolios) >= 20:
        return schedule.CancelJob

def track_portfolio_performance(portfolio, num_coins, workbook, portfolio_path):
    for month in range(1, 13):  # Track for 12 months
        track_time = portfolio['creation_date'] + timedelta(days=30 * month)
        updated_coin_data = get_coin_data_by_ids([coin.id for coin in portfolio['coins'].values()])

        total_return = 0
        worksheet = workbook[portfolio['creation_date'].strftime('%Y-%m-%d')]

        for coin_id, coin in portfolio['coins'].items():
            initial_price = coin.price
            updated_price = updated_coin_data.get(str(coin_id), {}).get('quote', {}).get('USD', {}).get('price', 0)
            investment = portfolio['coins'][coin_id].investment
            return_percentage = ((updated_price - initial_price) / initial_price) * 100
            total_return += return_percentage

            worksheet.append([f"Month {month}", initial_price, updated_price, return_percentage])

        average_return = total_return / num_coins
        worksheet.append(['Total Return', 'Average Return', average_return])

        workbook.save(portfolio_path)
        workbook.close()

        if len(portfolios) >= 20:
            return schedule.CancelJob

portfolios = []

if __name__ == "__main__":
    create_and_track_portfolios()
