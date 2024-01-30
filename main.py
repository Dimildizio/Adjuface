import asyncio
import logging
import yaml
from aiogram import Bot, Dispatcher
from bot.message_handler import setup_handlers
from bot.db_requests import initialize_database


async def main(dp, iobot):
    setup_handlers(dp, get_token())
    await dp.start_polling(iobot)


def get_token():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config['token']


async def init_database():
    await initialize_database()


if __name__ == '__main__':
    logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARN)
    ibot = Bot(token=get_token())
    dispatcher = Dispatcher()
    asyncio.run(init_database())
    asyncio.run(main(dispatcher, ibot))
