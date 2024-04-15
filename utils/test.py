import asyncio
import aiohttp
from config import CONTRACT_ABI, ARBITRUM_RPC_URL as RPC_URL, CONTRACT_ADDRESS, api_key as API_KEY
from datetime import datetime


async def get_burnt_tokens_from_trans(tx_data):
    # Simulating an asynchronous operation, such as fetching data or a sleep
    await asyncio.sleep(0)  # This is just a placeholder and can be removed

    # Extract the 'input' field from the transaction data
    input_data = tx_data['input']

    # Check if input data is at least the size of methodId + address + minimal token data
    if len(input_data) < 74:
        return "Invalid input data length"

    # The amount is located after the first 74 characters (method ID + address)
    amount_hex = input_data[74:]
    print(f"Hex Amount: {amount_hex}")  # Debugging
    # Convert hexadecimal to decimal
    amount_dec = int(amount_hex, 16)
    tokens = amount_dec / 10 ** 18
    return tokens


async def fetch_transactions(from_address, to_address, api_key):
    url = f"https://api.arbiscan.io/api?module=account&action=txlist&address={from_address}&startblock=0&endblock=99999999&sort=asc&apikey={api_key}"

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            ssl=False,
            limit=1,  # or use_dns_cache=False
    )) as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                transactions = data.get('result', [])
                relevant_transactions = [tx for tx in transactions if to_address in tx['input']]
                return relevant_transactions
            else:
                return f"Failed to fetch transactions, status code: {response.status}"


def timestamp_to_datetime(unix_timestamp):
    """Convert Unix timestamp to datetime."""
    return datetime.utcfromtimestamp(int(unix_timestamp))


async def fetch_transactions_by_date(from_address, to_address, api_key, start_date, end_date):
    url = f"https://api.arbiscan.io/api?module=account&action=txlist&address={from_address}&startblock=0&endblock=99999999&sort=asc&apikey={api_key}"

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            ssl=False,
            limit=1,  # or use_dns_cache=False
    )) as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                transactions = data.get('result', [])
                filtered_transactions = []
                for tx in transactions:
                    tx_date = timestamp_to_datetime(tx['timeStamp'])
                    if start_date <= tx_date <= end_date:
                        if to_address in tx['input']:
                            filtered_transactions.append(tx)
                return filtered_transactions
            else:
                return f"Failed to fetch transactions, status code: {response.status}"


async def main():
    FROM_ADDRESS = '0xD44257ddE89ca53F1471582f718632e690e46Dc2'
    TO_ADDRESS = 'dead'
    start_date = datetime(2024, 1, 1)  # Start of the year 2023
    end_date = datetime(2024, 12, 31)  # End of the year 2023
    transactions = await fetch_transactions_by_date(FROM_ADDRESS, TO_ADDRESS, API_KEY, start_date, end_date)
    if transactions:
        for tx in transactions:
            burnt_token = await get_burnt_tokens_from_trans(tx)
            print(tx['hash'], burnt_token)  # Printing hash and the number of burnt tokens
    else:
        print("No relevant transactions found.")

if __name__ == "__main__":
    asyncio.run(main())
