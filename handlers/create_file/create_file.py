import requests
from web3 import Web3
import asyncio
import aiohttp
from config import CONTRACT_ABI, ARBITRUM_RPC_URL as RPC_URL, CONTRACT_ADDRESS, api_key as API_KEY
from datetime import datetime, timedelta
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
from config import api_key
from datetime import datetime
from utils.utils import format_large_number, timestamp_to_datetime
from utils.asyncUtils import get_burnt_tokens_from_trans, fetch_transactions_by_date
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def create_transaction_report(transactions):
    filename = os.path.join(BASE_DIR, "", "transaction_report.txt")

    with open(filename, "w") as file:
        for tx in transactions:
            burnt_tokens = await get_burnt_tokens_from_trans(tx)
            formatted_tokens = format_large_number(burnt_tokens)
            timestamp = int(tx['timeStamp'])
            date = timestamp_to_datetime(tx['timeStamp'])

            # Assemble all transaction info into one string.
            tx_info = (
                f"Transaction Hash: {tx['hash']}\n"
                f"From: {tx['from']}\n"
                f"To: DEAD(((((\n"
                f"Amount: {formatted_tokens} Tokens\n"  # Assuming the 'value' field, need conversion if in wei
                f"Date: {date}\n"  # Include formatted date
                "\n"  # Add a newline for spacing between transactions
            )
            # Write the assembled transaction info to the file at once.
            file.write(tx_info)
    return filename


async def main():
    from_address = '0xD44257ddE89ca53F1471582f718632e690e46Dc2'
    to_address = 'dead'
    now = datetime.utcnow()
    start_date = now - timedelta(days=30)  # Default last 30 days for monthly data
    end_date = now  # End date is current time
    transactions = await fetch_transactions_by_date(from_address, to_address, api_key, start_date, end_date)
    # Pass a list containing the transaction dictionary
    await create_transaction_report(transactions)


if __name__ == "__main__":
    asyncio.run(main())
