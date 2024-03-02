"""
This module centralizes the configuration settings, localization strings, and preloaded resources for the Telegram bot.
It facilitates easy management and access to common resources and settings that are used throughout the bots
operations.

Key Contents:
- Preloaded collages and category images for guiding user selections in the face swapping process.
- Configuration settings such as the FastAPI service URL, Telegram bot path, and rate limiting parameters.
- Localization strings for supporting multilingual user interactions and providing responses, prompts, and error
  messages.
- Contact information and other static data loaded from configuration files
"""


from aiogram.types import FSInputFile
from utils import get_yaml, load_target_names, get_localization


CONTACTS = get_yaml()
CONFIG = get_yaml('config.yaml')
LANGUAGE = CONFIG['language']

FACE_EXTRACTION_URL = CONFIG['fastapi_swapper']
TGBOT_PATH = CONFIG['bot_path']
TGBOT_NAME = CONFIG['bot_name']

DATABASE_FILE = CONFIG['db_name']
ASYNC_DB_URL = f'{CONFIG["db_type"]}:///{DATABASE_FILE}'

DELAY_BETWEEN_IMAGES = CONFIG['img_delay']

HOUR_INTERVAL = CONFIG['hour_interval']
PREMIUM_DAYS = CONFIG['premium_days']
FREE_REQUESTS = CONFIG['free_requests']
PREMIUM_REQUESTS = CONFIG['premium_requests']
PREMIUM_TARGETS = CONFIG['premium_targets']

DATEFORMAT = '%Y-%m-%d'

LOCALIZATION = get_localization(lang=LANGUAGE)

TARGETS = load_target_names(LANGUAGE)
PRELOADED_COLLAGES = {category: FSInputFile(collage_path) for category, collage_path in TARGETS['collages'].items()}

TTS_LINK = CONFIG['tts_link']
STT_LINK = CONFIG['stt_link']
TTS_AUTH = CONFIG['tts_auth']
TTS_TOKEN = CONFIG['tts_token']
TTS_AUDIO_SIZE = CONFIG['tts_audio_size']

CURRENCY_URL = CONFIG['currency_url']
CURRENCY_API = CONFIG['currency_api']

WEATHER_URL = CONFIG['weather_url']
WEATHER_API = CONFIG['weather_api']

YOUTOK = CONFIG['you_token']
YOUNUM = CONFIG['you_num']
PRICE = CONFIG['price']

UTIL_FOLDER = CONFIG['util_folder']
