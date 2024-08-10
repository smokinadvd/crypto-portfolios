import requests
import pandas as pd
from datetime import datetime, timedelta
import os

# Define the API endpoint and the provided API key
api_key = "8e58e4ac-182a-4c41-ac41-6f7032cfd47c"
url_latest = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
url_quotes = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': api_key,
}

# Function to create a new portfolio
def create_new_portfolio(min_market_cap=100000):
    params = {
        'start': '1',
        'limit': '1000',
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
                    filtered_meme_coins.append({
                        'ID': id,
                        'Symbol': symbol,
                        'Name': name,
                        'Price': price,
                        'Market Cap': market_cap,
                        '24h Change': change_24h,
                        '7d Change': change_7d,
                        'Date Added': coin.get('date_added', '1970-01-01T00:00:00Z'),
                        'Timestamp': timestamp
                    })
                if len(filtered_meme_coins) >= 100:
                    break
    else:
        print(f"Error fetching latest coins: {response.status_code}")

    df = pd.DataFrame(filtered_meme_coins)
    return df

# Function to update the portfolio
def update_portfolio(portfolio_id, df, months=12):
    portfolio_path = 'portfolios.xlsx'
    with pd.ExcelWriter(portfolio_path, engine='openpyxl', mode='a') as writer:
        for month in range(months):
            monthly_date = (datetime.now() + pd.DateOffset(months=month)).strftime('%Y-%m')
            for index, row in df.iterrows():
                coin_id = row['ID']
                params = {'id': coin_id, 'convert': 'USD'}
                response = requests.get(url_quotes, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()['data'][str(coin_id)]['quote']['USD']
                    df.loc[index, f'Price {monthly_date}'] = data['price']
                    df.loc[index, f'Market Cap {monthly_date}'] = data['market_cap']
                    df.loc[index, f'24h Change {monthly_date}'] = data['percent_change_24h']
                    df.loc[index, f'7d Change {monthly_date}'] = data['percent_change_7d']
                else:
                    print(f"Error updating coin {coin_id}: {response.status_code}")
            # Save the updated portfolio
            df.to_excel(writer, sheet_name=f'{portfolio_id}_{monthly_date}')

def main():
    portfolio_path = 'portfolios.xlsx'
    if not os.path.exists(portfolio_path):
        with pd.ExcelWriter(portfolio_path, engine='openpyxl') as writer:
            pass

    # Create a new portfolio each month
    portfolio_id = datetime.now().strftime('portfolio_%Y_%m')
    df = create_new_portfolio()

    # Save the new portfolio to a new sheet
    with pd.ExcelWriter(portfolio_path, engine='openpyxl', mode='a') as writer:
        df.to_excel(writer, sheet_name=portfolio_id)

    # Update the portfolio for 12 months
    update_portfolio(portfolio_id, df)

if __name__ == "__main__":
    main()
