import asyncio
from datetime import datetime, timedelta

from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    FSInputFile
)
from web3 import Web3
from web3.middleware import geth_poa_middleware

from config import api_key, text_list, callback_data_list, CONTRACT_ADDRESS, CONTRACT_ABI, ARBITRUM_RPC_URL as RPC_URL
from utils.asyncUtils import (fetch_total_supply, get_current_supply, get_burned_percent,
                              fetch_transactions_by_date, get_burnt_tokens_from_trans, calculate_burned_tokens,
                              fetch_dexview_token_data, add_chat_id, get_burnt_tokens, get_burnt_tokens_weekly
                              )
from utils.utils import (button_builder, fetch_transactions_by_quantity, format_large_number,
                         format_price, timestamp_to_datetime
                         )

router = Router()


@router.message(CommandStart())
async def start_handler(message: types.Message):
    start_message = (
        "🚀 *Welcome to the Token Growth Bot!*\n\n"
        "I can assist you with the latest statistics and updates on token performance. "
        "Use the commands provided to get real-time data and subscribe to weekly updates.\n\n"
        "To see a full list of commands, type /help\n\n"
        "*TOKEN S GROWTH IS INEVITABLE*"
    )
    await message.answer(start_message, parse_mode="Markdown")


@router.message(Command('help'))
async def help_handler(message: types.Message):
    help_message = (
        "🆘 Need some help? Here's what I can do for you:\n\n"
        "/week_statistics - Fetch and display statistics for the past week.\n"
        "/getid - Find out the ID of the current chat.\n"
        "/lastburns - Show the most recent token burn transactions.\n"
        "/subscribe - Sign up for automatic weekly updates sent directly to this chat.\n\n"
        "Simply type any of these commands to get started. If you have any questions or need further assistance, feel free to reach out!"
    )
    await message.answer(help_message)


@router.message(Command('getid'))
async def send_chat_id(message: types.Message):
    chat_id = message.chat.id
    await message.reply(f"This chat's ID is: {chat_id}")


@router.message(Command('week_statistics'))
async def week_statistics(message: types.Message):
    web3 = Web3(Web3.HTTPProvider(RPC_URL))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    from_address = CONTRACT_ADDRESS
    now = datetime.utcnow()
    start_date = now - timedelta(days=7)
    end_date = now

    contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
    total_supply, burned_amount, transactions = await asyncio.gather(
        fetch_total_supply(contract),
        get_burnt_tokens(),
        fetch_transactions_by_date(from_address, api_key, start_date, end_date)
    )
    current_supply = await get_current_supply(burned_amount, total_supply)
    burned_percent = await get_burned_percent(total_supply, burned_amount)

    if isinstance(transactions, str):
        await message.answer(transactions)
        return

    burned_tokens = await get_burnt_tokens_weekly()

    dex_info = await fetch_dexview_token_data(
        CONTRACT_ADDRESS)
    if not dex_info or 'pairs' not in dex_info or len(dex_info['pairs']) == 0:
        await message.answer("Failed to fetch token data from DexView.")
        return

    pair_info = dex_info['pairs'][0]  # Assuming we want the first pair
    price_usd = format_price(pair_info['priceUsd'])
    liquidity_usd = pair_info['liquidity']['usd']
    alert_message = "📊 <b>Weekly Token Report</b> 📊"
    stats_message = (
        f"{alert_message}\n\n"
        f"📅 Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
        f"🔥 Total Burned Tokens in the Last 7 Days: {format_large_number(burned_tokens)} Tokens\n"
        f"🔥 Burned Percentage: {burned_percent:.2f}%\n"
        f"🏦 Current Supply: {format_large_number(current_supply)} Tokens\n"
        f"💵 Price (USD): ${price_usd}\n"
        f"💧 Liquidity (USD): ${format_large_number(liquidity_usd)}\n\n"
        f"📈 <a href='https://www.dextools.io/app/en/arbitrum/pair-explorer/0xbee32bffb0cd21278acd8b00786b6e840e7a7108?t=1715520319056'>Chart</a> |  "
        f"💹 <a href='https://www.sushi.com/swap?outputCurrency=0xd44257dde89ca53f1471582f718632e690e46dc2'>Trade</a> |  "
        f"📊 <a href='https://arbiscan.io/address/0xd44257dde89ca53f1471582f718632e690e46dc2'>Token</a>"
    )

    await message.answer_photo(
        photo="AgACAgIAAxkBAAICNmZBDDMHwAsaQ-HklZlQLX_tatwdAALl3TEbaU8ISkKOB1wyeJOOAQADAgADeQADNQQ",
        caption=stats_message, parse_mode="HTML")


# @router.message()
# async def handle_photo(message: types.Message):
#     photo = message.photo[-1]
#     file_id = photo.file_id
#
#     await message.reply(f"Received your photo. File ID: {file_id}")

@router.message(Command('lastburns'))
async def last_burns(message: types.Message):
    keyboard = await button_builder(text_list, callback_data_list)
    keyboard.adjust(1, 1)
    await message.answer("Choose the number of transactions or time range:", reply_markup=keyboard.as_markup())


@router.message(Command('subscribe'))
async def send_chat_id(message: types.Message):
    chat_id = message.chat.id
    await add_chat_id(chat_id)
    await message.reply(f"This chat's ID is: {chat_id}. You will now receive weekly updates.")


@router.callback_query(lambda c: c.data and c.data.startswith('burnLastMonth'))
async def handle_burn_month_query(callback_query: types.CallbackQuery):
    from_address = '0xD44257ddE89ca53F1471582f718632e690e46Dc2'
    now = datetime.utcnow()
    start_date = now - timedelta(days=30)
    end_date = now
    transactions = await fetch_transactions_by_date(from_address, api_key, start_date, end_date)

    if transactions:
        report_filename = await get_burnt_tokens_from_trans(transactions)

        document = FSInputFile(f"{report_filename}")
        await callback_query.message.answer_document(document,
                                                     caption="Here is your monthly transaction report.")
    else:
        await callback_query.message.answer("No transactions found for the specified criteria.")

    await callback_query.answer()


@router.callback_query(lambda c: c.data and c.data.startswith('burn_'))
async def handle_burn_query(callback_query: types.CallbackQuery):
    action = callback_query.data
    from_address = '0xD44257ddE89ca53F1471582f718632e690e46Dc2'
    to_address = 'dead'
    transactions = None
    if action == "burn_last_5":
        transactions = await fetch_transactions_by_quantity(from_address, to_address, api_key, 5)
    elif action == "burn_last_10":
        transactions = await fetch_transactions_by_quantity(from_address, to_address, api_key, 10)

    if transactions:
        reply_texts = []
        for tx in transactions:
            burnt_tokens = await get_burnt_tokens_from_trans(tx)
            formatted_tokens = format_large_number(burnt_tokens)
            date = timestamp_to_datetime(tx["timeStamp"])
            tx_info = (
                f"🔥 Burnt Tokens: {formatted_tokens} Tokens\n"
                f"📅 Date: {date}\n"
                f"📤 From: {tx['from']}\n"
                f"🔗 [Hash: {tx['hash'][:10]}...]<a href='https://arbiscan.io/tx/{tx['hash']}'>View Transaction</a>"
            )
            reply_texts.append(tx_info)

        full_message_text = '\n\n'.join(reply_texts)

        if len(full_message_text) > 4096:
            full_message_text = "🔥 The message is too long to display. Please check the blockchain explorer."
        keyboard = await button_builder(text_list, callback_data_list)
        keyboard.adjust(1, 1)
        await callback_query.message.edit_text(
            full_message_text,
            parse_mode='HTML',
            disable_web_page_preview=True,
            reply_markup=keyboard.as_markup()
        )
    else:
        await callback_query.message.edit_text("No transactions found for the specified criteria.")

    await callback_query.answer()


async def prepare_week_statistics():
    web3 = Web3(Web3.HTTPProvider(RPC_URL))
    web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    contract = web3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)
    total_supply = await fetch_total_supply(contract)
    burned_amount = await get_burnt_tokens()
    current_supply = await get_current_supply(burned_amount, total_supply)
    burned_percent = await get_burned_percent(total_supply, burned_amount)

    from_address = CONTRACT_ADDRESS
    now = datetime.utcnow()
    start_date = now - timedelta(days=7)
    end_date = now

    burned_tokens = await get_burnt_tokens_weekly()
    dex_info = await fetch_dexview_token_data(
        CONTRACT_ADDRESS)
    pair_info = dex_info['pairs'][0]
    price_usd = format_price(pair_info['priceUsd'])
    liquidity_usd = pair_info['liquidity']['usd']

    alert_message = "📊 <b>Weekly Token Statistics Report</b> 📊"
    stats_message = (
        f"{alert_message}\n\n"
        f"📅 Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n"
        f"🔥 Total Burned Tokens in the Last 7 Days: {format_large_number(burned_tokens)} Tokens\n"
        f"🔥 Burned Percentage: {burned_percent:.2f}%\n"
        f"🏦 Current Supply: {format_large_number(current_supply)} Tokens\n"
        f"💵 Price (USD): ${price_usd}\n"
        f"💧 Liquidity (USD): ${format_large_number(liquidity_usd)}\n\n"
        f"📈 <a href='https://www.dextools.io/app/en/arbitrum/pair-explorer/0xbee32bffb0cd21278acd8b00786b6e840e7a7108?t=1715520319056'>Chart</a> |  "
        f"💹 <a href='https://www.sushi.com/swap?outputCurrency=0xd44257dde89ca53f1471582f718632e690e46dc2'>Trade</a> |  "
        f"📊 <a href='https://arbiscan.io/address/0xd44257dde89ca53f1471582f718632e690e46dc2'>Token</a>"
    )

    return stats_message

# async def main():
#     a = await prepare_week_statistics()
#     print(a)
#
# if __name__ == "__main__":
#     asyncio.run(main())