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
