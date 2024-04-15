import asyncio
from .utils import timestamp_to_datetime, format_large_number
import aiohttp
from web3 import Web3
from web3.middleware import geth_poa_middleware
from config import CONTRACT_ABI, ARBITRUM_RPC_URL as RPC_URL, CONTRACT_ADDRESS, api_key, chat_collection
from datetime import datetime, timedelta

# Constants
DECIMALS = 10 ** 18  # Adjust this according to the token's decimals


async def fetch_total_supply(contract):
    loop = asyncio.get_event_loop()
    total_supply = await loop.run_in_executor(None, contract.functions.totalSupply().call)
    return total_supply / DECIMALS  # Convert to full tokens


async def fetch_balance(contract, address):
    loop = asyncio.get_event_loop()
    balance = await loop.run_in_executor(None, contract.functions.balanceOf(address).call)
    return balance / DECIMALS  # Convert to full tokens


async def get_current_supply(burned_tokens, total_tokens):
    return total_tokens - burned_tokens


async def get_burned_percent(total, burned):
    return (burned / total) * 100 if total > 0 else 0  # Calculate percentage


async def fetch_dexview_token_data(token_addresses="0xD44257ddE89ca53F1471582f718632e690e46Dc2"):
    url = f"https://openapi.dexview.com/latest/dex/tokens/{token_addresses}"
    headers = {
        "Accept": "application/json",
        # Add any other necessary headers here
    }

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            ssl=False,
            limit=1,  # or use_dns_cache=False
    )) as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()

                return data
            else:
                print(f"Error fetching data, status code: {response.status}")
                return None


def parse_token_amount(input_data):
    # Example: assuming the last 64 hex characters represent the amount in a transfer(input, amount) call
    hex_amount = input_data[-64:]
    return int(hex_amount, 16) / (10 ** 18)  # Adjust for token's decimals


async def fetch_transactions_by_date(from_address="0xD44257ddE89ca53F1471582f718632e690e46Dc2",
                                     to_address="dead", api_key=api_key,
                                     start_date=None, end_date=None):
    if start_date is None:
        start_date = datetime.utcnow() - timedelta(days=7)
    if end_date is None:
        end_date = datetime.utcnow()
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
    # print(f"Hex Amount: {amount_hex}")  # Debugging
    # Convert hexadecimal to decimal
    amount_dec = int(amount_hex, 16)
    tokens = amount_dec / 10 ** 18
    return tokens


async def create_transaction_report(transactions):
    filename = "transaction_report.txt"
    with open("handlers/" + filename, "w") as file:
        for tx in transactions:
            burnt_tokens = await get_burnt_tokens_from_trans(tx)
            formatted_tokens = format_large_number(burnt_tokens)

            # Convert the Unix timestamp to a human-readable date
            timestamp = int(tx['timeStamp'])
            date = timestamp_to_datetime(tx['timeStamp'])

            # Assemble all transaction info into one string.
            tx_info = (
                f"Transaction Hash: {tx['hash']}\n"
                f"From: {tx['from']}\n"
                f"To: {tx['to']}\n"
                f"Amount: {formatted_tokens} Tokens\n"  # Assuming the 'value' field, need conversion if in wei
                f"Date: {date}\n"  # Include formatted date
                "\n"  # Add a newline for spacing between transactions
            )
            # Write the assembled transaction info to the file at once.
            file.write(tx_info)
    return filename


async def calculate_burned_tokens(transactions):
    total_burned = 0
    for tx in transactions:
        if 'dead' in tx['input']:  # Check if the transaction is a burn transaction
            burned_amount = parse_token_amount(tx['input'])
            total_burned += burned_amount

    return total_burned  # Convert to a human-readable format


async def add_chat_id(chat_id):
    await chat_collection.update_one(
        {'chat_id': chat_id},
        {'$setOnInsert': {'chat_id': chat_id}},
        upsert=True
    )


async def get_all_chat_ids():
    cursor = chat_collection.find({})
    return [doc['chat_id'] for doc in await cursor.to_list(length=None)]


async def remove_chat_id(chat_id):
    await chat_collection.delete_one({'chat_id': chat_id})


async def main():
    a = await fetch_dexview_token_data()
    print(a)


if __name__ == "__main__":
    asyncio.run(main())
