from aiogram.types import FSInputFile
from utils import get_yaml, load_target_names, get_localization

CONTACTS = get_yaml()
CONFIG = get_yaml('config.yaml')

TARGETS = load_target_names(CONFIG['language'])
PRELOADED_COLLAGES = {category: FSInputFile(collage_path) for category, collage_path in TARGETS['collages'].items()}
FACE_EXTRACTION_URL = CONFIG['fastapi_swapper']
TGBOT_PATH = CONFIG['bot_path']
DELAY_BETWEEN_IMAGES = CONFIG['img_delay']
LOCALIZATION = get_localization(lang=CONFIG['language'])
