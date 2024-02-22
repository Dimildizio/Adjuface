
from datetime import datetime, timedelta
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Any, Union

from bot.handlers.constants import HOUR_INTERVAL
from bot.database.db_models import ErrorLog, SchedulerLog, async_engine
from bot.database.db_fetching import fetch_scheduler_logs
from bot.database.db_users import exist_user_check, insert_message
from bot.database.db_images import create_image_entry, update_image_entry


async def log_error(user_id: Optional[int], error_message: str, details: Optional[str] = None) -> None:
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            error_log = ErrorLog(
                user_id=user_id,
                error_message=error_message,
                details=details
            )
            session.add(error_log)
            await session.commit()


async def log_scheduler_run(job_name: str, status: str = "success", details: str = None,
                            hour_delay: int = HOUR_INTERVAL):
    """
    Logs a scheduler run if hour interval hours have passed since the last run, or creates an entry if none exists.

    :param job_name: The name of the job that was run.
    :param status: The status of the job run (default is 'success').
    :param details: Optional details about the job run.
    :param hour_delay: The delay in hours to check against the last run time (default is hour interval hours).
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Check the last entry for the job
            last_entry = await session.execute(
                select(SchedulerLog)
                .filter_by(job_name=job_name)
                .order_by(desc(SchedulerLog.run_datetime))
                .limit(1)
            )
            last_entry = last_entry.scalar_one_or_none()

            now = datetime.now()

            # If there's no last entry or hour interval hours have passed since the last run, log a new entry
            if not last_entry or now - last_entry.run_datetime >= timedelta(hours=hour_delay):
                new_log = SchedulerLog(job_name=job_name, status=status, details=details)
                session.add(new_log)
                await session.commit()
                print(f"Logged new run for {job_name}.")
            else:
                print(f"No need to log {job_name} yet.")
            await fetch_scheduler_logs(job_name)


# exist_user_check - wrappers don't want to async work
async def log_text_data(message: Any) -> None:
    """
    Log text data from a message to a message and user table.

    :param message: The user's tg object.
    :return: None
    """
    await exist_user_check(message.from_user)
    text = message.text.replace(' ', '_')
    await insert_message(message.from_user.id, text)


# exist_user_check - wrappers don't want to async work
async def log_input_image_data(message: Any, input_image_name: str) -> None:
    """
    Log input image data to an image and user table.

    :param message: The user's tg message object.
    :param input_image_name: The name of the input image.
    :return: None
    """
    await exist_user_check(message.from_user)
    await create_image_entry(message.from_user.id, input_image_name)


async def log_output_image_data(message: Any, input_image_name: str,
                                output_image_names: Union[str, List[str], None]) -> None:
    """
    Log output image data.

    :param message: The user's tg message object.
    :param input_image_name: The name of the input image.
    :param output_image_names: The name(s) of the output image(s).
    :return: None
    """
    await exist_user_check(message.from_user)
    await update_image_entry(message.from_user.id, input_image_name, output_image_names)
