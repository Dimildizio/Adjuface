import asyncio
import logging
import yaml
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.message_handler import setup_handlers
from bot.db_requests import initialize_database, update_user_quotas
from typing import Any


async def main(dp: Any, iobot: Any) -> None:
    """
    Starts the polling process for the bot.

    :param dp: Dispatcher for handling updates.
    :param iobot: The IO-bound operations bot.
    :return: None
    """
    setup_handlers(dp, get_token())
    await dp.start_polling(iobot)


def get_token() -> str:
    """
    Reads the API token from a configuration file.

    :return: API token as a string.
    """
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config['token']


def list_all_loggers() -> None:
    """
    Initializes the database asynchronously.

    :return: None
    """
    # logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.ERROR)
    root_logger = logging.getLogger('')
    loggers = [root_logger] + [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    # if 'sqlalchemy' in name]
    logger_info = {}
    for logger in loggers:
        if 'sqlalchemy' in logger.name:
            logger.setLevel(logging.ERROR)
        logger_info[logger.name] = logger.getEffectiveLevel()
    return logger_info


if __name__ == '__main__':
    print(list_all_loggers())
    scheduler = AsyncIOScheduler()
    ibot = Bot(token=get_token())
    dispatcher = Dispatcher()
    asyncio.run(initialize_database())
    scheduler.add_job(update_user_quotas, 'cron', hour=0, minute=0, second=0, timezone='UTC')
    asyncio.run(main(dispatcher, ibot))
    scheduler.start()
