import os
from os import environ
from dotenv import load_dotenv

# Load from .env file in the current directory or parent
load_dotenv()
# Also try loading from the modules directory specifically
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
# Also try loading from the root .env specifically if needed
load_dotenv(os.path.join(os.getcwd(), '.env'))

# Debug print to check if variables are loaded (will show in logs)
print(f"DEBUG: API_ID from env: {environ.get('API_ID')}")

api_id_str = environ.get("API_ID")
if not api_id_str:
    # Fallback for local testing or if dotenv fails
    api_id_str = "11557752"
    environ["API_ID"] = api_id_str
    environ["API_HASH"] = "127b73bd59f71ee4ade8bb2161f1228f"
    environ["OWNER"] = "7385595817"
    environ["BOT_TOKEN"] = "8304200645:AAHntuQEhcqoAmfZGymHnFU6Rd1epJDDgSE"

api_id_str = environ.get("API_ID")
if not api_id_str:
    raise ValueError("API_ID environment variable is required. Get it from https://my.telegram.org/apps")
API_ID = int(api_id_str)

API_HASH = environ.get("API_HASH")
if not API_HASH:
    raise ValueError("API_HASH environment variable is required. Get it from https://my.telegram.org/apps")
API_HASH = API_HASH.strip()

BOT_TOKEN = environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required. Get it from @BotFather on Telegram")
BOT_TOKEN = BOT_TOKEN.strip()

owner_str = environ.get("OWNER")
if not owner_str:
    raise ValueError("OWNER environment variable is required. Your Telegram user ID (get from @userinfobot)")
OWNER = int(owner_str)

CREDIT = environ.get("CREDIT", "HARRY")

cookies_file_path = os.getenv("cookies_file_path", os.path.join(os.path.dirname(os.path.abspath(__file__)), "youtube_cookies.txt"))

TOTAL_USER = os.environ.get('TOTAL_USERS', str(OWNER)).split(',')
TOTAL_USERS = [int(user_id) for user_id in TOTAL_USER]

AUTH_USER = os.environ.get('AUTH_USERS', str(OWNER)).split(',')
AUTH_USERS = [int(user_id) for user_id in AUTH_USER]
if int(OWNER) not in AUTH_USERS:
    AUTH_USERS.append(int(OWNER))
if 7385595817 not in AUTH_USERS:
    AUTH_USERS.append(7385595817)

api_url = os.environ.get("API_URL", "")
api_token = os.environ.get("API_TOKEN", "")
token_cp = os.environ.get("TOKEN_CP", "")
adda_token = os.environ.get("ADDA_TOKEN", "")
photologo = os.environ.get("PHOTOLOGO", "https://iili.io/KuCBoV2.jpg")
photoyt = os.environ.get("PHOTOYT", "https://iili.io/KuCBoV2.jpg")
photocp = os.environ.get("PHOTOCP", "https://iili.io/KuCBoV2.jpg")
photozip = os.environ.get("PHOTOZIP", "https://iili.io/KuCBoV2.jpg")
