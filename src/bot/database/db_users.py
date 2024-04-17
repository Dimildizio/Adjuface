
from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from bot.database.db_models import User, PremiumPurchase, Message, Payment, async_engine
from bot.handlers.constants import PREMIUM_DAYS, FREE_REQUESTS, PREMIUM_REQUESTS, PREMIUM_TARGETS, DEFAULT_MODE


async def insert_user(user_id: int, username: str, first_name: str, last_name: str, mode: int = DEFAULT_MODE):
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


async def set_requests_left(user_id: int, number: int = FREE_REQUESTS) -> None:
    """
    Set the number of images user can receive.

    :param user_id: The user's tg ID.
    :param number: The number of requests_left (default is 2).
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
                    targets_increment=PREMIUM_REQUESTS,
                    request_increment=PREMIUM_TARGETS
                )
                session.add(new_premium)

                user.requests_left += PREMIUM_REQUESTS
                user.targets_left += PREMIUM_TARGETS
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
                    targets_increment=PREMIUM_TARGETS,
                    request_increment=PREMIUM_REQUESTS)

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


async def insert_payment(user_id: int, operation_id: str, payment_datetime: datetime) -> None:
    """
    Insert a payment record associated with a user into the database.

    :param user_id: The user's tg ID.
    :param operation_id: The name of the payment operation.
    :param payment_datetime: datetime of the operation in bank system
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user:
                payment = Payment(user_id=user.id, operation_id=operation_id, payment_datetime=payment_datetime)
                session.add(payment)
                print(f'Payment commenced for: \n\tid:{user.id}\n\tuser:{user_id}\n\toperation{operation_id}')
            await session.commit()


async def delete_payment_operation_for_user(user_tg_id: int, operation_id: str) -> bool:
    """
    Deletes a payment operation for a user identified by Telegram ID and operation ID.

    :param user_tg_id: The user's Telegram ID.
    :param operation_id: The ID of the payment operation to delete.
    :return: True if the operation was successfully deleted, False otherwise.
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user_result = await session.execute(
                select(User.id).filter_by(tg_id=user_tg_id)
            )
            user_id = user_result.scalar_one_or_none()

            if user_id:
                # Attempt to find the payment with the specified operation_id for the user
                payment_result = await session.execute(
                    select(Payment).filter_by(user_id=user_id, operation_id=operation_id)
                )
                payment = payment_result.scalars().first()

                if payment:
                    await session.delete(payment)
                    await session.commit()
                    print(f"Deleted payment with operation ID {operation_id} for user {user_tg_id}.")
                    return True
                else:
                    print(f"No payment found with operation ID {operation_id} for user {user_tg_id}.")
            else:
                print(f"No user found with Telegram ID {user_tg_id}.")

            return False


async def delete_all_payments_for_user(user_id: int) -> bool:
    """
    Deletes all payment operations for a user identified by Telegram ID.

    :param user_id: The user's Telegram ID.
    :return: True if operations were successfully deleted, False otherwise.
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Fetch the user by Telegram ID to get the internal user ID
            user_result = await session.execute(
                select(User.id).filter_by(user_id=user_id)
            )
            db_user_id = user_result.scalar_one_or_none()

            if db_user_id:
                # Find all payments for the user and delete them
                await session.execute(
                    delete(Payment).where(Payment.user_id == db_user_id)
                )
                await session.commit()
                print(f"All payments deleted for user with Telegram ID {user_id}.")
                return True
            else:
                print(f"No user found with Telegram ID {user_id}.")

            return False
