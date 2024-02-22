import asyncio
import logging
import yaml
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.message_handler import setup_handlers
#from bot.db_requests import initialize_database, update_user_quotas, log_scheduler_run, clear_outdated_images
from bot.database.db_models import initialize_database
from bot.database.db_updates import update_user_quotas
from bot.database.db_images import clear_outdated_images
from bot.database.db_logging import log_scheduler_run
from utils import remove_old_image, backup_database
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
    logger_info = {}
    for logger in loggers:
        if 'sqlalchemy' in logger.name:
            logger.setLevel(logging.ERROR)
        logger_info[logger.name] = logger.getEffectiveLevel()


async def remove_imgs_log() -> None:
    td = 24
    await remove_old_image()
    await log_scheduler_run("remove_old_image", "success", "Completed removing old images", td)
    await clear_outdated_images(td)
    await log_scheduler_run("clear_outdated_images_for_all_users", "success",
                            f"Completed clearing outdated images entry logs older than {td} hours", td)
    await backup_database()
    await log_scheduler_run("backup_database", "success", "Backed up database", td)


async def start_scheduler() -> None:
    """
    Starts the scheduler and adds jobs to run every 24 hours.
    """
    scheduler = AsyncIOScheduler()
    scheduler.add_job(update_user_quotas, 'cron', hour=0, minute=0, second=0, timezone='UTC')
    scheduler.add_job(remove_imgs_log, 'cron', hour=0, minute=0, second=0, timezone='UTC')
    scheduler.start()
    # Keep the scheduler running in the background
    while True:
        await asyncio.sleep(3600)


async def run_bot_and_scheduler() -> None:
    """
    Initializes the bot, database, and starts both the bot and the scheduler concurrently.
    """
    token = get_token()
    bot = Bot(token=token)
    dp = Dispatcher()
    await initialize_database()
    # Run
    await asyncio.gather(
        start_scheduler(),
        main(dp, bot)
    )


if __name__ == '__main__':
    print(list_all_loggers())
    asyncio.run(run_bot_and_scheduler())
