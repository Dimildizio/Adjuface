"""
This module centralizes the configuration settings, localization strings, and preloaded resources for the Telegram bot.
It facilitates easy management and access to common resources and settings that are used throughout the bot's
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

FACE_EXTRACTION_URL = CONFIG['fastapi_swapper']
TGBOT_PATH = CONFIG['bot_path']

DATABASE_FILE = CONFIG['db_name']
ASYNC_DB_URL = f'{CONFIG["db_type"]}:///{DATABASE_FILE}'

DELAY_BETWEEN_IMAGES = CONFIG['img_delay']

HOUR_INTERVAL = CONFIG['hour_interval']
PREMIUM_DAYS = CONFIG['premium_days']

DATEFORMAT = '%Y-%m-%d'

LOCALIZATION = get_localization(lang=CONFIG['language'])

TARGETS = load_target_names(CONFIG['language'])
PRELOADED_COLLAGES = {category: FSInputFile(collage_path) for category, collage_path in TARGETS['collages'].items()}
