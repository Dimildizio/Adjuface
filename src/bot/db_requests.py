"""
This module, db_requests.py, provides an asynchronous interface to interact with a SQLite database using
SQLAlchemy and aiosqlite. It defines models for Users, Messages, and ImageNames, leveraging SQLAlchemy's ORM
capabilities for database operations. The module supports operations such as initializing the database, inserting
and updating user information, handling message and image name records, and adjusting user quotas.

Key Features:
- Asynchronous database engine creation and session management using SQLAlchemy's async capabilities.
- ORM model definitions for User, Message, and ImageName, facilitating easy data manipulation and query construction.
- Utility functions for database initialization, user data manipulation (insertion, updates), message logging,
  image name handling, and user data fetching.
- Advanced user management features including premium status upgrades, request and target quota adjustments,
  and timestamp updates for user activities.

Usage:
The module is designed to be used in asynchronous Python applications where database interactions are required.
It includes functions to perform CRUD operations on user data, manage message and image name records, and retrieve
user-specific information efficiently. The async functions ensure non-blocking database operations, suitable for
I/O-bound applications like chatbots or web services.

Examples of operations include inserting a new user, updating a user's mode, decrementing request quotas, logging
messages, and fetching user data. These operations are encapsulated in async functions, which need to be awaited
when called.

Note: Before using this module, ensure the database file path and SQLAlchemy engine settings are correctly configured
for your application's requirements. Also make sure all necessary config and yaml files are set on the root level.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Dict, Optional, List, Any, Union

# Set  credentials and run DB
Base = declarative_base()  # Class name after all
DATABASE_FILE = 'user_database.db'
ASYNC_DB_URL = f'sqlite+aiosqlite:///{DATABASE_FILE}'
async_engine = create_async_engine(ASYNC_DB_URL, echo=True)


# import logging # not working - still outputs INFO level
# logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
# logging.getLogger('sqlite').setLevel(logging.ERROR)


class User(Base):
    __tablename__: str = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    mode = Column(Integer, default=1)
    receive_target_flag = Column(Integer, default=0)
    status = Column(String, default='free')
    requests_left = Column(Integer, default=10)
    targets_left = Column(Integer, default=0)
    last_photo_sent_timestamp = Column(TIMESTAMP, default=datetime.now())

    messages = relationship("Message", back_populates="user")
    image_names = relationship("ImageName", back_populates="user")


class Message(Base):
    __tablename__: str = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    text_data = Column(String)
    timestamp = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="messages")


class ImageName(Base):
    __tablename__: str = 'image_names'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    input_image_name = Column(String)
    output_image_names = Column(String)

    user = relationship("User", back_populates="image_names")

async def clear_output_images_by_user_id(user_id: int) -> None:
    """
    Clears (deletes) output image names associated with a given user ID.

    :param user_id: The Telegram ID of the user whose output images are to be cleared.
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            image_name_records = await session.execute(
                select(ImageName).filter_by(user_id=user_id)
            )
            image_names = image_name_records.scalars().all()

            for image_name in image_names:
                image_name.output_image_names = ''
                image_name.input_image_name = ''
            await session.commit()


async def initialize_database() -> None:
    """"
    Initialize and create the tables in the database asynchronously
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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
                    user.status = 'free'
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
                user.requests_left += 100
                user.targets_left += 10
                user.status = "premium"
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


async def fetch_image_names_by_user_id(user_id: int) -> Dict[str, Optional[str]]:
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
                image_name_dict[image_name.input_image_name] = image_name.output_image_names
        return image_name_dict


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
                                  output_image_names=None)
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
            else:
                print("Entry not found for update.")
            await session.commit()


async def exist_user_check(message: Any) -> None:
    """
    Check if a user exists and insert their information if not.
    Should be a wrapper but it throws coroutine TypeError

    :param message: The user's aiogram Message object.
    :return: None
    """
    user_id = message.from_user.id
    username = message.from_user.username or ''
    first_name = message.from_user.first_name or ''
    last_name = message.from_user.last_name or ''
    await insert_user(user_id, username, first_name, last_name)


# exist_user_check - wrappers don't want to async work
async def log_text_data(message: Any) -> None:
    """
    Log text data from a message to a message and user table.

    :param message: The user's tg object.
    :return: None
    """
    await exist_user_check(message)
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
    await exist_user_check(message)
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
    await exist_user_check(message)
    await update_image_entry(message.from_user.id, input_image_name, output_image_names)


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


async def format_userdata_output(user: User, messages: str) -> None:
    """
    Format user data output.

    :param user: The User object.
    :param messages: A string containing user messages.
    :return: None
    """
    image_names_dict = await fetch_image_names_by_user_id(user.user_id)
    if image_names_dict:
        image_names = '\n\t\t\t'.join([f"original: {input_image} "
                                       f"output [{len(output_images.split(',')) if output_images else 0} img]:"
                                       f"{output_images})" for input_image, output_images in image_names_dict.items()])

        print(f"\nUser: {user.username} (ID:{user.user_id} Name: {user.first_name} {user.last_name})"
              f"\n\tMode: {user.mode} Custom targets left: {True if user.receive_target_flag else False} "
              f"- {user.targets_left}"
              f"\n\tStatus: {user.status}"
              f"\n\tImages total: {len(image_names_dict.values()) + len(image_names_dict.keys())}"
              f" left: {user.requests_left}"
              f"\n\tMessages: [{messages}]"
              f"\n\tImages: [{image_names}]")
    else:
        print(f"User: {user.username}, Messages: [{messages}], Images: []")


async def return_user(user: User) -> Dict[str, Union[int, str, bool, Column]]:
    """
    Return user data as a dictionary.

    :param user: The User object.
    :return: A dictionary containing user data.
    """
    return {'user_id': user.user_id, 'username': user.username, 'first_name': user.first_name,
            'last_name': user.last_name, 'mode': user.mode, 'status': user.status,
            'requests_left': user.requests_left, 'targets_left': user.targets_left}


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
            # return user.receive_target_flag


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


async def update_user_quotas(free_requests: int = 10, premium_requests: int = 100, targets: int = 10) -> None:
    """
    Update user quotas based on their status.

    :param free_requests: The number of requests for free users.
    :param premium_requests: The number of requests for premium users.
    :param targets: The number of targets for users.
    :return: None
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            users = await session.execute(select(User))
            users = users.scalars().all()
            for user in users:
                if user.status == 'free' and user.requests_left < free_requests:
                    user.requests_left = free_requests
                elif user.status == 'premium':
                    if user.requests_left < premium_requests:
                        user.requests_left = premium_requests
                    if user.targets_left < targets:
                        user.targets_left = targets
            await session.commit()
