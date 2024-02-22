
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from bot.database.db_models import User, PremiumPurchase, Message, async_engine
from bot.handlers.constants import PREMIUM_DAYS


async def insert_user(user_id: int, username: str, first_name: str, last_name: str, mode: int = 1):
    """
    Inserts a new user or updates an existing user's information.

    :param user_id: The user's tg ID.
    :param username: The username of the user.
    :param first_name: The first name of the user.
    :param last_name: The last name of the user.
    :param mode: The user's mode (default is 1).
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            existing_user = await session.execute(select(User).filter_by(user_id=user_id))
            existing_user = existing_user.scalar_one_or_none()
            # Avoid sql injection
            username = username.replace(' ', '_')
            first_name = first_name.replace(' ', '_')
            last_name = last_name.replace(' ', '_')
            if existing_user is None:

                user = User(user_id=user_id, username=username, first_name=first_name, last_name=last_name, mode=mode)
                session.add(user)
            else:
                existing_user.username = username
                existing_user.first_name = first_name
                existing_user.last_name = last_name
            await session.commit()


async def update_user_mode(user_id: int, mode: str):
    """
    Updates the mode of an existing user.

    :param user_id: The user's tg ID.
    :param mode: The new user mode.
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user:
                user.mode = mode
            await session.commit()


async def decrement_requests_left(user_id: int, n: int = 1) -> None:
    """
    Decrements the max number of images user can receive.

    :param user_id: The user's tg ID.
    :param n: The number to decrement (default is 1).
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user:
                if user.requests_left > 0:
                    n = user.requests_left - n
                    user.requests_left = max(0, n)
                else:
                    user.requests_left = 0
            await session.commit()


async def decrement_targets_left(user_id: int, n: int = 1) -> None:
    """
    Decrements the number of targets user can upload.

    :param user_id: The user's tg ID.
    :param n: The number to decrement (default is 1).
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user and user.targets_left > 0:
                n = user.targets_left - n
                user.targets_left = max(0, n)
            await session.commit()


async def set_requests_left(user_id: int, number: int = 10) -> None:
    """
    Set the number of images user can receive.

    :param user_id: The user's tg ID.
    :param number: The number of requests_left (default is 10).
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user:
                user.status = 'free'
                user.premium_expiration = None
                await delete_premium_purchases_by_user_id(user_id)
                user.targets_left = 0
                user.requests_left = number
            await session.commit()


async def buy_premium(user_id: int) -> None:
    """
    Upgrade a user to premium and update their quotas.

    :param user_id: The user's tg ID.
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()

            if user:
                new_expiration_date = datetime.now() + timedelta(days=PREMIUM_DAYS)

                # Create a new PremiumPurchase record
                new_premium = PremiumPurchase(
                    user_id=user.user_id,
                    purchase_date=datetime.now().date(),
                    expiration_date=new_expiration_date.date(),
                    targets_increment=10,
                    request_increment=100
                )
                session.add(new_premium)

                user.requests_left += 100
                user.targets_left += 10
                user.status = "premium"
                user.premium_expiration = new_expiration_date  # 30 days for premium
            await session.commit()


async def exist_user_check(user: Any) -> None:
    """
    Check if a user exists and insert their information if not.
    Should be a wrapper but it throws coroutine TypeError

    :param user: The user aiogram object.
    :return: None
    """
    user_id = user.id
    username = user.username or ''
    first_name = user.first_name or ''
    last_name = user.last_name or ''
    await insert_user(user_id, username, first_name, last_name)


async def toggle_receive_target_flag(user_id: int, flag: int = 0):
    """
    Switches states for target images to put faces onto. Available only for premium users.
    :param user_id: The tg ID of the user.
    :param flag: on-off value to switch the flag
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user:
                user.receive_target_flag = flag
                await session.commit()


async def add_premium_purchase_for_premium_users():
    """
    Add a PremiumPurchase instance for every user currently marked as premium.
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            premium_users = await session.execute(
                select(User).where(User.status == 'premium')
            )
            premium_users = premium_users.scalars().all()

            for user in premium_users:
                purchase_date = datetime.now()
                expiration_date = purchase_date + timedelta(days=PREMIUM_DAYS)

                new_purchase = PremiumPurchase(
                    user_id=user.user_id,
                    purchase_date=purchase_date,
                    expiration_date=expiration_date,
                    targets_increment=10,
                    request_increment=100)

                session.add(new_purchase)


async def delete_premium_purchases_by_user_id(user_id: int):
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Perform the deletion
            await session.execute(delete(PremiumPurchase).where(PremiumPurchase.user_id == user_id))
            await session.commit()


async def remove_expired_premium_purchases(user_id: int):
    """
    Remove expired PremiumPurchase entries for a specific user_id.

    :param user_id: The ID of the user whose expired PremiumPurchases should be removed.
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            await session.execute(delete(PremiumPurchase).where(
                                                            (PremiumPurchase.user_id == user_id) &
                                                            (PremiumPurchase.expiration_date < datetime.now().date())))
            await session.commit()


async def insert_message(user_id: int, text_data: str) -> None:
    """
    Insert a message associated with a user into a DB.

    :param user_id: The user's tg ID.
    :param text_data: The text data of the message.
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()

            if user:
                message = Message(user_id=user.id, text_data=text_data)
                session.add(message)
            await session.commit()
