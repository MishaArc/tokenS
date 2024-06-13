import requests
from web3 import Web3
import asyncio
import aiohttp
from config import CONTRACT_ABI, ARBITRUM_RPC_URL as RPC_URL, CONTRACT_ADDRESS, api_key as API_KEY
from datetime import datetime
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from datetime import datetime

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}


def get_total_supply(contract_address, api_key, decimals=18):
    url = f"https://api.arbiscan.io/api?module=stats&action=tokensupply&contractaddress={contract_address}&apikey={api_key}"
    response = requests.get(url)
    data = response.json()
    supply_in_units = int(data['result'])  # Convert the string result to integer
    adjusted_supply = supply_in_units / (10 ** decimals)  # Adjust based on token decimals
    return adjusted_supply


def get_burnt_tokens(contract_address, api_key, decimals=18):
    burn_addresses = [
        '0x000000000000000000000000000000000000dEaD',
        '0x0000000000000000000000000000000000000000'
    ]
    burnt_tokens_sum = 0
    max_results_per_page = 10000  # Set a reasonable limit for each page

    for burn_address in burn_addresses:
        page = 1
        while True:
            url = f"https://api.arbiscan.io/api?module=account&action=tokentx&contractaddress={contract_address}&address={burn_address}&page={page}&offset={max_results_per_page}&sort=desc&apikey={api_key}"
            response = requests.get(url)
            data = response.json()

            # Check if there are transactions returned and that it's not an error message
            if 'result' in data and isinstance(data['result'], list):
                # Process the transactions on the current page
                for tx in data['result']:
                    if tx['to'].lower() == burn_address.lower():
                        burnt_tokens_sum += int(tx['value'])

                # If the number of transactions is less than the maximum, we've reached the last page
                if len(data['result']) < max_results_per_page:
                    break

                # Increment the page number to get the next set of transactions
                page += 1
            else:
                # If there's no result key or there's an error, stop the loop
                break

    # Convert from smallest unit to the appropriate unit by applying the decimals
    burnt_tokens_sum /= (10 ** decimals)
    return burnt_tokens_sum

def get_current_supply(contract_address, api_key, initial_supply, decimals=18):
    # Get the number of burned tokens
    burnt_tokens = get_burnt_tokens(contract_address, api_key, decimals)
    # Subtract burned tokens from the initial supply to get current supply
    current_supply = initial_supply - burnt_tokens
    return current_supply


def get_current_supply_from_contract(contract_address):
    w3 = Web3(Web3.HTTPProvider('https://arb1.arbitrum.io/rpc'))  # Adjust the provider URL
    contract = w3.eth.contract(address=contract_address, abi=CONTRACT_ABI)
    current_supply = contract.functions.totalSupply().call()
    return current_supply / (10 ** 18)  # Adjust for decimals if necessary


def get_token_info(network, token_address):
    url = f"https://api.geckoterminal.com/api/v2/networks/{network}/tokens/{token_address}"
    response = requests.get(url, headers=headers)
    try:
        # Attempt to parse JSON only if the response was successful
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': 'API request failed', 'status_code': response.status_code, 'message': response.text}
    except ValueError:  # Includes simplejson.decoder.JSONDecodeError
        return {'error': 'Failed to decode JSON', 'status_code': response.status_code, 'message': response.text}


def timestamp_to_datetime(unix_timestamp):
    """Convert Unix timestamp to datetime."""
    return datetime.utcfromtimestamp(int(unix_timestamp))


async def button_builder(text_list: list, callback: list, ) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for text in range(len(text_list)):
        builder.add(types.InlineKeyboardButton(
            text=text_list[text],
            callback_data=callback[text])
        )
    return builder


async def fetch_transactions_by_quantity(from_address, to_address, api_key, last_n=None):
    url = f"https://api.arbiscan.io/api?module=account&action=txlist&address={from_address}&startblock=0&endblock=99999999&sort=desc&apikey={api_key}"  # 'sort=desc' to get the latest transactions first

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False, limit=1)) as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                transactions = data.get('result', [])
                relevant_transactions = [tx for tx in transactions if to_address in tx['input']]

                # Return only the last 'last_n' transactions if specified, otherwise return all
                return relevant_transactions[:last_n] if last_n is not None else relevant_transactions
            else:
                return f"Failed to fetch transactions, status code: {response.status}"


def format_large_number(number):
    if number is None:
        return "N/A"  
    if number < 1_000:
        return f"{number}"
    elif number < 1_000_000:
        return f"{number / 1_000:.3f}K"  # Thousands
    elif number < 1_000_000_000:
        return f"{number / 1_000_000:.3f}M"  # Millions
    elif number < 1_000_000_000_000:
        return f"{number / 1_000_000_000:.3f}B"  # Billions
    else:
        return f"{number / 1_000_000_000_000:.3f}T"  # Trillions


def format_price(value):
    """Format very small floating-point numbers to string with visible leading zeros."""
    if value == 0:
        return "0.0"

    formatted_value = f"{value:.20f}"  # Use more precision and strip trailing zeros
    # Remove trailing zeros and potential unnecessary decimal point
    formatted_value = formatted_value.rstrip('0').rstrip('.')
    # Handle very small numbers that start with '0.'
    if formatted_value.startswith("0.00000"):
        return "0." + formatted_value[2:]
    return formatted_value


print(get_burnt_tokens(contract_address=CONTRACT_ADDRESS, api_key=API_KEY))

# Usage example
# network = 'arbitrum'  # Specify the correct network
# token_address = '0xd44257dde89ca53f1471582f718632e690e46dc2'
# token_info = get_token_info(network, token_address)
#
#
# # Example usage
# contract_address = CONTRACT_ADDRESS
# total_supply = get_total_supply(contract_address, api_key, 18)
# burnt_tokens = get_burnt_tokens(contract_address, api_key, 18)
# current_supply = get_current_supply(contract_address, api_key, total_supply)
