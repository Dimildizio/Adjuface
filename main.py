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


def list_all_loggers():
    #logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.ERROR)
    root_logger = logging.getLogger('')
    loggers = [root_logger] + [logging.getLogger(name) for name in logging.root.manager.loggerDict]# if 'sqlalchemy' in name]
    logger_info = {}
    for logger in loggers:
        if 'sqlalchemy' in logger.name:
            logger.setLevel(logging.ERROR)
        logger_info[logger.name] = logger.getEffectiveLevel()
    return logger_info


if __name__ == '__main__':
    print(list_all_loggers())
    ibot = Bot(token=get_token())
    dispatcher = Dispatcher()
    asyncio.run(init_database())
    asyncio.run(main(dispatcher, ibot))
