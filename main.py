import asyncio
import logging
import yaml
from aiogram import Bot, Dispatcher
from bot.message_handler import setup_handlers


async def main(dp, iobot):
    setup_handlers(dp)
    await dp.start_polling(iobot)


def get_token():
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config['token']


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    ibot = Bot(token=get_token())
    dispatcher = Dispatcher()
    asyncio.run(main(dispatcher, ibot))

