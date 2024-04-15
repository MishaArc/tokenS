import asyncio
from os import getenv
import json
from dotenv import load_dotenv
from pathlib import Path
from web3 import Web3
import motor.motor_asyncio
load_dotenv()

config_dir = Path(__file__).parent

abi_file_path = config_dir / 'contract_abi.json'

with open(abi_file_path, 'r') as abi_file:
    api_response = json.load(abi_file)

TELEGRAM_TOKEN = getenv("TOKEN")

ARBITRUM_RPC_URL = 'https://arb1.arbitrum.io/rpc'

CONTRACT_ADDRESS = '0xD44257ddE89ca53F1471582f718632e690e46Dc2'

CONTRACT_ABI = json.loads(api_response['result'])

w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC_URL))

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

api_key = getenv("API_KEY")

headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Accept': 'application/json',  # Assuming JSON responses are expected
        'Content-Type': 'application/json'  # If you're sending data to the API, specify the content type
    }

text_list = [
        "🖐 Last 5 Transactions",
        "🔟 Last 10 Transactions",
        "🗓️ Last Month",
        "⚙️ Custom Range"
    ]
callback_data_list = [
        "burn_last_5",
        "burn_last_10",
        "burnLastMonth",
        "burn_custom_range"
    ]

db_client = motor.motor_asyncio.AsyncIOMotorClient(getenv("MONGO_URI"), tlsAllowInvalidCertificates=True)

db = db_client[getenv("MONGO_DB_NAME")]
chat_collection = db[getenv("MONGO_COLLECTION")]
