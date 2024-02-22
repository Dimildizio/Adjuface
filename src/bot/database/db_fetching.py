from sqlalchemy import select, Column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Dict, List, Any, Optional, Union

from bot.database.db_models import ImageName, User, SchedulerLog, PremiumPurchase, ErrorLog, async_engine
from bot.handlers.constants import DATEFORMAT


async def fetch_image_names_by_user_id(user_id: int) -> Dict[str, Any]:
    """
    Fetch image names associated with a user by their user ID.

    :param user_id: The user's tg ID.
    :return: A dictionary mapping DBs input image names to output image names (or None if no output image names exist).
    """
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(ImageName).filter_by(user_id=user_id)
        )
        image_names = result.scalars().all()

        image_name_dict = {}
        if image_names:
            for image_name in image_names:
                image_name_dict[image_name.input_image_name] = {
                    "output_image_names": image_name.output_image_names,
                    "timestamp": image_name.timestamp.strftime(DATEFORMAT)}
        return image_name_dict


async def fetch_user_data(user_id: int) -> Optional[Any]:
    """
    Fetch user data from the database tables.

    :param user_id: The tg ID of the user.
    :return: A User object or None if the user is not found.
    """
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id).options(selectinload(User.messages)))
        user = result.scalar_one_or_none()

        if user:
            messages = ', '.join([message.text_data for message in user.messages])
            await format_userdata_output(user, messages)
            return user
        else:
            print("User not found")
            return None


async def fetch_user_by_id(user_id: int) -> Optional[User]:
    """
    Fetch a user by their tg ID.

    :param user_id: The tg ID of the user to fetch.
    :return: The User object or None if not found.
    """
    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(User).filter_by(user_id=user_id))
        user = result.scalar_one_or_none()
        return user


async def format_userdata_output(user: User, messages: str) -> None:
    """
    Format user data output.

    :param user: The User object.
    :param messages: A string containing user messages.
    :return: None
    """
    print('_' * 50)
    image_names_dict = await fetch_image_names_by_user_id(user.user_id)
    if image_names_dict:
        image_names = '\n\t\t\t'.join([
                     f"original: {input_image} timestamp: {details['timestamp']}\n\t\t\t\t"
                     f"output [{len(details['output_image_names'].split(',')) if details['output_image_names'] else 0}"
                     f" img]: {details['output_image_names']})" for input_image, details in image_names_dict.items()])

        n = sum([len(details['output_image_names'].split(','))
                 if details['output_image_names'] else 0 for details in image_names_dict.values()])

        premium_purchases = await fetch_premium_purchases_by_user_id(user.user_id)
        premium_purchases_output = '\n\t\t\t'.join([
            f"Purchase Date: {purchase['purchase_date']}, Expiration Date: {purchase['expiration_date']}, "
            f"Targets Increment: {purchase['targets_increment']}, Requests Increment: {purchase['request_increment']}"
            for purchase in premium_purchases
        ])

        print(f"\n\n\nUser: {user.username} (ID:{user.user_id} Name: {user.first_name} {user.last_name})"
              f"\n\tMode: {user.mode} \n\tCustom targets left: {True if user.receive_target_flag else False} "
              f"- {user.targets_left} til {user.premium_expiration}"
              f"\n\tPremium Purchases: [{premium_purchases_output if premium_purchases_output else 'None'}]"
              f"\n\tStatus: {user.status}"
              f"\n\tRequests total: {len(image_names_dict.keys())} + {n}"
              f" left: {user.requests_left}"
              f"\n\tMessages: [{messages}]"
              f"\n\tImages: [{image_names}]")
    else:
        print(f"\n\n\nUser: {user.username} {user.user_id}, Messages: [{messages}], Images: []")


async def fetch_scheduler_logs(job_name: str = None):
    """
    Fetches entries from the scheduler_logs table, optionally filtered by a specific job name.

    :param job_name: Optional. The name of the job to filter logs by.
    :return: A list of dictionaries containing log entries.
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            if job_name:
                query = select(SchedulerLog).where(SchedulerLog.job_name == job_name).order_by(
                    SchedulerLog.run_datetime.desc())
            else:
                query = select(SchedulerLog).order_by(SchedulerLog.run_datetime.desc())
            result = await session.execute(query)
            logs = result.scalars().all()

            log_entries = [
                {"id": log.id,
                 "job_name": log.job_name,
                 "run_datetime": log.run_datetime,
                 "status": log.status,
                 "details": log.details}
                for log in logs]
            print(log_entries)
            return log_entries


async def fetch_premium_purchases_by_user_id(user_id: int) -> list:
    """
    Fetch premium purchase records for a user.

    :param user_id: The user's ID.
    :return: A list of dictionaries, each representing a premium purchase.
    """
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(PremiumPurchase)
            .where(PremiumPurchase.user_id == user_id)
            .order_by(PremiumPurchase.purchase_date)
        )
        purchases = result.scalars().all()
        return [
               {"purchase_date": purchase.purchase_date.strftime(DATEFORMAT),
                "expiration_date": purchase.expiration_date.strftime(DATEFORMAT),
                "targets_increment": purchase.targets_increment,
                "request_increment": purchase.request_increment} for purchase in purchases]


async def return_user(user: User) -> Dict[str, Union[int, str, bool, Column]]:
    """
    Return user data as a dictionary.

    :param user: The User object.
    :return: A dictionary containing user data.
    """
    return {'user_id': user.user_id, 'username': user.username, 'first_name': user.first_name,
            'last_name': user.last_name, 'mode': user.mode, 'status': user.status,
            'requests_left': user.requests_left, 'targets_left': user.targets_left,
            'premium_expiration': {user.premium_expiration}}


async def fetch_all_user_ids() -> List[int]:
    """
    Fetch all user tg IDs from the database.

    :return: A list of user tg IDs.
    """
    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(User.user_id))
        user_ids = result.scalars().all()
        return user_ids


async def fetch_all_users_data() -> None:
    """
    Print data for all users to console.

    :return: None
    """
    all_user_ids = await fetch_all_user_ids()
    for user_id in all_user_ids:
        await fetch_user_data(user_id)


async def fetch_recent_errors(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch the most recent error logs.

    :param limit: The number of recent error logs to fetch.
    :return: A list of dictionaries, each representing an error log.
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            result = await session.execute(
                select(
                    ErrorLog.id,
                    ErrorLog.user_id,
                    ErrorLog.error_message,
                    ErrorLog.details,
                    ErrorLog.timestamp,
                    User.username,
                    User.first_name,
                    User.last_name)
                .join(User, ErrorLog.user_id == User.user_id, isouter=True)
                .order_by(ErrorLog.timestamp.desc())
                .limit(limit)
            )
            error_logs = result.all()
            recent_errors = [{
                "id": error_log.id,
                "user_id": error_log.user_id,
                "error_message": error_log.error_message,
                "details": error_log.details,
                "timestamp": error_log.timestamp,
                "username": error_log.username,
                "first_name": error_log.first_name,
                "last_name": error_log.last_name
            } for error_log in error_logs]
            return recent_errors
