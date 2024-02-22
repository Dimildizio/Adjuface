
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from bot.handlers.constants import HOUR_INTERVAL
from bot.database.db_models import User, ImageName, async_engine


async def clear_output_images_by_user_id(user_id: int, hour_delay: int = HOUR_INTERVAL) -> None:
    """
    Clears (deletes) output image names associated with a given user ID.

    :param user_id: The Telegram ID of the user whose output images are to be cleared.
    :param hour_delay: How often should the data be cleaned.
    :return: None
    """
    cutoff_time = datetime.now() - timedelta(hours=hour_delay)
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            await session.execute(
                delete(ImageName)
                .where(ImageName.user_id == user_id, ImageName.timestamp < cutoff_time)
            )
            await session.commit()


async def clear_outdated_images(hour_delay: int = HOUR_INTERVAL):
    """
    Clears outdated output images for all users in the database.

    :param hour_delay: The age threshold in hours for an image to be considered outdated.
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            result = await session.execute(select(User.user_id))
            user_ids = result.scalars().all()
    for user_id in user_ids:
        await clear_output_images_by_user_id(user_id, hour_delay)
        print(f"Cleared outdated images for user ID: {user_id}")


async def create_image_entry(user_id: int, input_image_name: str) -> None:
    """
    Create a new image entry for a user.

    :param user_id: The user's tg ID.
    :param input_image_name: The input image name.
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Create a new entry in ImageName table
            new_entry = ImageName(user_id=user_id,
                                  input_image_name=input_image_name,
                                  output_image_names=None,
                                  timestamp=datetime.now())
            session.add(new_entry)
            await session.commit()


async def update_image_entry(user_id: int, input_image_name: str, output_image_names: List[str]) -> None:
    """
    Update an existing image entry for user.

    :param user_id: The user's tg ID to map inputs table to.
    :param input_image_name: The input image name to map outputs to.
    :param output_image_names: List of output image names.
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            existing_entry = await session.execute(select(ImageName).filter_by(
                user_id=user_id, input_image_name=input_image_name))
            existing_entry = existing_entry.scalar_one_or_none()
            str_outputs = ','.join(output_image_names) if output_image_names else None
            if existing_entry:
                existing_entry.output_image_names = str_outputs
                existing_entry.timestamp = datetime.now()
            else:
                print("Entry not found for update.")
            await session.commit()
