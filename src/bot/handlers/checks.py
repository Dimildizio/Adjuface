"""
This module contains utility functions and checks that support the bot's operations by managing rate limiting,
verifying user permissions for certain actions, and handling common tasks like updating user statuses or logging errors.

Key Functionalities:
- Rate limiting to prevent spamming and ensure fair resource usage among users.
- Checks for user's request limits and time constraints to manage access to the bot's image processing features.
- Utility functions for common tasks such as toggling user flags, updating modes, and decrementing available requests.
- Error logging and display functionalities to assist in monitoring and troubleshooting the bot's operations.

Usage:
- These utility functions are invoked across various parts of the bot's workflow, particularly in handling
  commands, processing images, and responding to callback queries. They ensure that user interactions are
  managed smoothly and within defined operational parameters.

Example:
- Before processing an image request, `check_limit` and `check_time_limit` are used to verify that the user
  has not exceeded their allowed number of requests or is sending requests too frequently.

Dependencies:
- Application-specific database request functions: For querying and updating user data.
- Localization and constants: For accessing predefined messages and configuration settings.
"""


from aiogram.types import Message, FSInputFile
from datetime import datetime, timedelta
from typing import Any

from bot.database.db_users import exist_user_check, toggle_receive_target_flag, update_user_mode, decrement_targets_left
from bot.database.db_fetching import fetch_user_data, fetch_recent_errors, fetch_scheduler_logs, fetch_user_by_id
from bot.database.db_updates import update_photo_timestamp
from bot.database.db_logging import log_error
from bot.handlers.constants import LOCALIZATION, DELAY_BETWEEN_IMAGES


SENT_TIME = {}


async def check_limit(user: Any, message: Message) -> bool:
    """
    Checks if the user has reached their request limit.

    :param user: The user class object.
    :param message: The user data message from the user.
    :return: True if the user has requests left, False otherwise.
    """
    if user.requests_left <= 0:
        await message.answer(LOCALIZATION['no_attempts'])
        return False
    return True


async def check_time_limit(user: Any, message: Message, n_time: int = 20) -> bool:
    """
    Checks if a user has reached a time limit for an action.

    :param user: The user class object.
    :param message: The message obj.
    :param n_time: The time limit in seconds (default is 20).
    :return: True if the user is within the time limit, False otherwise.
    """
    if user.status == 'premium':
        return True
    if (datetime.now() - user.last_photo_sent_timestamp) < timedelta(seconds=n_time):
        await message.answer(LOCALIZATION['too_fast'])
        return False
    return True


async def prevent_multisending(message: Message) -> bool:
    """
    Prevents multiple messages from being sent in a short time.

    :param message: The message object.
    :return: True if the message can be sent, False otherwise.
    """
    dt = datetime.now()
    last_sent = SENT_TIME.get(message.from_user.id, None)
    if message.media_group_id is None and (last_sent is None or (
            dt - last_sent).total_seconds() >= DELAY_BETWEEN_IMAGES):
        SENT_TIME[message.from_user.id] = dt
        return True
    return False


async def image_handler_checks(message: Message) -> Any:
    """
    Checks the user status and limits.

    :param message: The message with user data.
    :return: User data if checks pass, else None.
    """
    await exist_user_check(message.from_user)
    user = await fetch_user_data(message.from_user.id)
    if not (await check_limit(user, message) and await check_time_limit(user, message)):
        return None
    await update_photo_timestamp(user.user_id, datetime.now())
    return user


async def target_image_check(message: Message, user: Any, input_image: str) -> bool:
    """
    Checks if the user is eligible to send a target image and updates user mode accordingly.

    :param message: The message with user data.
    :param user: The user db object.
    :param input_image: The input image path.
    :return: The input image path if conditions are met, None otherwise.
    """
    if user.status == 'premium' and user.receive_target_flag and user.targets_left:
        await update_user_mode(user.user_id, input_image)
        await toggle_receive_target_flag(user.user_id)
        await message.answer(LOCALIZATION['target_uploaded'].format(left=user.targets_left - 1))
        await decrement_targets_left(user.user_id)  # due to async it does not keep up with m.answer
        return True


async def display_recent_errors():
    recent_errors = await fetch_recent_errors(limit=5)  # Fetch the last 5 errors
    if recent_errors:
        print("Recent Errors:")
        for error in recent_errors:
            user_info = f"User ID: {error['user_id']}, Username: {error['username']}, Name: {error['first_name']} " \
                        f"{error['last_name']}" if error['user_id'] else "User ID: None"
            print(f"ID: {error['id']}, {user_info}, "
                  f"Message: {error['error_message']}, Details: {error['details']}, "
                  f"Timestamp: {error['timestamp']}")
    else:
        print("No recent errors found.")


async def is_premium(message):
    """
    Sets the user to be able to send a new target image if they meet the criteria.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message.from_user)
    user = await fetch_user_by_id(message.from_user.id)
    if user.status == 'premium':
        return True
    await message.answer(LOCALIZATION['not_premium'])


async def utility_func(message: Message) -> None:
    """
    Dev func to do situational stuff to the user.

    :param message: The message with user data.
    :return: None
    """
    try:
        await fetch_scheduler_logs()
        send_path = r'C:\Users\tessa\Downloads\prog1.png'
        print('Working on', send_path)
        # await message.answer_video(FSInputFile(send_path))
        # await message.answer_photo(FSInputFile(send_path))
        # await message.answer("")
    except Exception as e:
        await log_error(message.from_user.id, error_message='UtilityFuncError: '+str(e))
        print('Attention! We got an error!', e)
    await display_recent_errors()
