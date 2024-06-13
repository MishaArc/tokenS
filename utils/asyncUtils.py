import asyncio
from .utils import timestamp_to_datetime, format_large_number
import aiohttp

from config import CONTRACT_ABI, ARBITRUM_RPC_URL as RPC_URL, CONTRACT_ADDRESS, api_key, chat_collection
from datetime import datetime, timedelta

# Constants
DECIMALS = 10 ** 18


async def fetch_total_supply(contract):
    loop = asyncio.get_event_loop()
    total_supply = await loop.run_in_executor(None, contract.functions.totalSupply().call)
    return total_supply / DECIMALS


async def fetch_balance(contract, address):
    loop = asyncio.get_event_loop()
    balance = await loop.run_in_executor(None, contract.functions.balanceOf(address).call)
    return balance / DECIMALS


async def get_current_supply(burned_tokens, total_tokens):
    return total_tokens - burned_tokens


async def get_burned_percent(total, burned):
    return (burned / total) * 100 if total > 0 else 0


async def fetch_dexview_token_data(token_addresses="0xD44257ddE89ca53F1471582f718632e690e46Dc2"):
    url = f"https://openapi.dexview.com/latest/dex/tokens/{token_addresses}"
    headers = {
        "Accept": "application/json",
        # Add any other necessary headers here
    }

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            ssl=False,
            limit=1,
    )) as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()

                return data
            else:
                print(f"Error fetching data, status code: {response.status}")
                return None


def parse_token_amount(input_data):
    hex_amount = input_data[-64:]
    return int(hex_amount, 16) / (10 ** 18)


async def fetch_transactions_by_date(from_address="0xD44257ddE89ca53F1471582f718632e690e46Dc2",
                                     api_key=api_key,
                                     start_date=None, end_date=None):
    burn_addresses = [
        '0x0000000000000000000000000000000000000000',
        '0x000000000000000000000000000000000000dead'
    ]

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
                        input_data = tx['input']
                        if input_data.startswith('0xa9059cbb'):
                            to_address = '0x' + input_data[34:74]
                            if to_address.lower() in [addr.lower() for addr in burn_addresses]:
                                filtered_transactions.append(tx)

                return filtered_transactions
            else:
                print(f"Failed to fetch transactions, status code: {response.status}")
                return []


async def get_burnt_tokens_from_trans(tx_data):
    await asyncio.sleep(0)

    input_data = tx_data['input']

    if len(input_data) < 74:
        return "Invalid input data length"

    amount_hex = input_data[74:]

    amount_dec = int(amount_hex, 16)
    tokens = amount_dec / 10 ** 18
    return tokens


async def create_transaction_report(transactions):
    filename = "transaction_report.txt"
    with open("handlers/" + filename, "w") as file:
        for tx in transactions:
            burnt_tokens = await get_burnt_tokens_from_trans(tx)
            formatted_tokens = format_large_number(burnt_tokens)

            date = timestamp_to_datetime(tx['timeStamp'])

            tx_info = (
                f"Transaction Hash: {tx['hash']}\n"
                f"From: {tx['from']}\n"
                f"To: {tx['to']}\n"
                f"Amount: {formatted_tokens} Tokens\n"  
                f"Date: {date}\n"  
                "\n"
            )
            file.write(tx_info)
    return filename


async def calculate_burned_tokens(transactions):
    burn_addresses = [
        '0000000000000000000000000000000000000000',
        '000000000000000000000000000000000000dead'
    ]

    total_burned = 0
    for tx in transactions:
        if any(burn_address in tx['input'].lower() for burn_address in burn_addresses):
            burned_amount = parse_token_amount(tx['input'])
            total_burned += burned_amount

    return total_burned


async def get_burned_in_a_week(transactions):
    total = 0
    for tx in transactions:
        burnt_tokens = await get_burnt_tokens_from_trans(tx)
        total += burnt_tokens
    return total


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


async def get_burnt_tokens(contract_address=CONTRACT_ADDRESS, api_key=api_key, decimals=18):
    burn_addresses = [
        '0x000000000000000000000000000000000000dEaD',
        '0x0000000000000000000000000000000000000000'
    ]
    burnt_tokens_sum = 0
    max_results_per_page = 10000

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            ssl=False,
    )) as session:
        for burn_address in burn_addresses:
            page = 1
            while True:
                url = f"https://api.arbiscan.io/api?module=account&action=tokentx&contractaddress={contract_address}&address={burn_address}&page={page}&offset={max_results_per_page}&sort=desc&apikey={api_key}"
                async with session.get(url) as response:
                    if response.status != 200:
                        print(f"Failed to fetch data, status code: {response.status}")
                        break
                    try:
                        data = await response.json()
                    except aiohttp.ContentTypeError:
                        print(f"Error decoding JSON at {url}")
                        break

                    if 'result' in data and isinstance(data['result'], list):
                        for tx in data['result']:
                            if tx['to'].lower() == burn_address.lower():
                                burnt_tokens_sum += int(tx['value'])

                        if len(data['result']) < max_results_per_page:
                            break

                        page += 1
                    else:
                        break

    burnt_tokens_sum /= (10 ** decimals)
    return burnt_tokens_sum


async def get_burnt_tokens_weekly(contract_address=CONTRACT_ADDRESS, api_key=api_key, decimals=18):
    burn_addresses = [
        '0x000000000000000000000000000000000000dEaD',
        '0x0000000000000000000000000000000000000000'
    ]
    burnt_tokens_sum = 0
    max_results_per_page = 10000

    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    now_timestamp = int(now.timestamp())
    seven_days_ago_timestamp = int(seven_days_ago.timestamp())

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            ssl=False,
            limit=1,
    )) as session:
        for burn_address in burn_addresses:
            page = 1
            while True:
                url = f"https://api.arbiscan.io/api?module=account&action=tokentx&contractaddress={contract_address}&address={burn_address}&page={page}&offset={max_results_per_page}&sort=desc&apikey={api_key}"
                async with session.get(url) as response:
                    if response.status != 200:
                        print(f"Failed to fetch data, status code: {response.status}")
                        break
                    try:
                        data = await response.json()
                    except aiohttp.ContentTypeError:
                        print(f"Error decoding JSON at {url}")
                        break

                    if 'result' in data and isinstance(data['result'], list):
                        for tx in data['result']:
                            tx_timestamp = int(tx['timeStamp'])
                            if seven_days_ago_timestamp <= tx_timestamp <= now_timestamp:
                                if tx['to'].lower() == burn_address.lower():
                                    burnt_tokens_sum += int(tx['value'])

                        if len(data['result']) < max_results_per_page:
                            break

                        page += 1
                    else:
                        break

    burnt_tokens_sum /= (10 ** decimals)
    return burnt_tokens_sum

