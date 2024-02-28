import asyncio
import yaml
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils import remove_old_files, backup_database, list_all_loggers
from typing import Any

from bot.database.db_models import initialize_database
from bot.database.db_updates import update_user_quotas
from bot.database.db_images import clear_outdated_images
from bot.database.db_logging import log_scheduler_run
from bot.message_handler import setup_handlers


async def main(dp: Any, io_bot: Any) -> None:
    """
    Starts the polling process for the bot.

    :param dp: Dispatcher for handling updates.
    :param io_bot: The IO-bound operations bot.
    :return: None
    """
    setup_handlers(dp, get_token())
    await dp.start_polling(io_bot)


def get_token() -> str:
    """
    Reads the API token from a configuration file.

    :return: API token as a string.
    """
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config['token']


async def remove_files_log(td: int = 24) -> None:
    await remove_old_files()
    await log_scheduler_run("remove_old_file", "success", "Completed removing old images", td)

    await remove_old_files(('temp\\voice',), name_start='audio')
    await log_scheduler_run("remove_old_file", "success", "Completed removing old audio", td)

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
    scheduler.add_job(remove_files_log, 'cron', hour=0, minute=0, second=0, timezone='UTC')
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
                         main(dp, bot))


if __name__ == '__main__':
    print(list_all_loggers())
    asyncio.run(run_bot_and_scheduler())
