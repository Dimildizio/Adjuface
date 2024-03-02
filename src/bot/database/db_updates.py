from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db_models import User, PremiumPurchase, async_engine
from bot.database.db_logging import log_scheduler_run
from bot.handlers.constants import HOUR_INTERVAL,FREE_REQUESTS


async def update_photo_timestamp(user_id: int, timestamp: datetime) -> None:
    """
    Update the last photo sent timestamp for a user to prevent them from sending multiple photos at once.

    :param user_id: The tg ID of the user.
    :param timestamp: The timestamp to set.
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user:
                user.last_photo_sent_timestamp = timestamp
            await session.commit()


async def update_user_quotas(free_requests: int = FREE_REQUESTS, td: int = HOUR_INTERVAL) -> None:
    """
    Update user quotas based on their status.

    :param free_requests: The number of requests for free users.
    :param td: time interval to check.
    :return: None
    """

    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Fetch all users
            users = await session.execute(select(User))
            users = users.scalars().all()

            for user in users:
                await session.execute(delete(PremiumPurchase).where(
                        (PremiumPurchase.user_id == user.user_id) &
                        (PremiumPurchase.expiration_date < datetime.now().date())))

                # Fetch all active premium purchases for the user
                active_purchases = await session.execute(select(PremiumPurchase).where(
                        PremiumPurchase.user_id == user.user_id,
                        PremiumPurchase.expiration_date >= datetime.now().date()))
                active_purchases = active_purchases.scalars().all()

                if active_purchases:
                    # Calculate the total increments for requests and targets from active purchases
                    total_request_increment = sum(purchase.request_increment for purchase in active_purchases)
                    total_targets_increment = sum(purchase.targets_increment for purchase in active_purchases)

                    # Update the user's quotas based on the total increments from active purchases
                    user.requests_left = total_request_increment
                    user.targets_left = total_targets_increment
                else:
                    # No active premium purchases - revert the user to free status
                    user.status = 'free'
                    user.requests_left = free_requests
                    user.premium_expiration = None  # Clear the premium expiration date
            await session.commit()
    await log_scheduler_run("update_user_quotas", "success", "Completed updating user quotas", td)


async def run_sync_db_operation(operation: callable) -> None:
    """
        Run a synchronous database operation.

        :param operation: A callable function that performs a database operation.
        :return: None
        """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            operation(session)
            await session.commit()
