from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime
DATABASE_FILE = 'user_database.db'
ASYNC_DB_URL = f'sqlite+aiosqlite:///{DATABASE_FILE}'
# import logging
# logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
# logging.getLogger('sqlite').setLevel(logging.ERROR)

Base = declarative_base()
async_engine = create_async_engine(ASYNC_DB_URL, echo=True)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    mode = Column(Integer, default=1)
    status = Column(String, default='free')
    requests_left = Column(Integer, default=10)
    last_photo_sent_timestamp = Column(TIMESTAMP, default=datetime.now())

    messages = relationship("Message", back_populates="user")
    image_names = relationship("ImageName", back_populates="user")


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    text_data = Column(String)
    timestamp = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="messages")


class ImageName(Base):
    __tablename__ = 'image_names'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    input_image_name = Column(String)
    output_image_names = Column(String)

    user = relationship("User", back_populates="image_names")


async def initialize_database():
    """"
    Initialize and create the tables in the database asynchronously
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def insert_user(user_id, username, first_name, last_name, mode=1):
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


async def update_user_mode(user_id, mode):
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user:
                user.mode = mode
            await session.commit()


async def fetch_user_mode(user_id):
    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(User.mode).where(User.user_id == user_id))
        user_mode = result.scalar_one_or_none()
        return user_mode


async def decrement_requests_left(user_id, n=1):
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


async def set_requests_left(user_id, number=10):
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user:
                user.requests_left = number
            await session.commit()


async def buy_premium(user_id):
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user:
                user.requests_left += 100
                user.status = "premium"
            await session.commit()


async def insert_message(user_id, text_data):
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()

            if user:
                message = Message(user_id=user.id, text_data=text_data)
                session.add(message)
            await session.commit()


async def fetch_image_names_by_user_id(user_id):
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


async def create_image_entry(user_id, input_image_name, output_image_names=None):
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            # Create a new entry
            new_entry = ImageName(user_id=user_id,
                                  input_image_name=input_image_name,
                                  output_image_names=output_image_names)
            session.add(new_entry)
            await session.commit()


async def update_image_entry(user_id, input_image_name, output_image_names):
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


async def exist_user_check(message):
    # should be a wrapper but it throws coroutine TypeError
    user_id = message.from_user.id
    username = message.from_user.username or ''
    first_name = message.from_user.first_name or ''
    last_name = message.from_user.last_name or ''
    await insert_user(user_id, username, first_name, last_name)


# exist_user_check - wrappers don't want to async work
async def log_text_data(message):
    print('LOG_TEXT_DATA')
    await exist_user_check(message)
    text = message.text.replace(' ', '_')
    await insert_message(message.from_user.id, text)


# exist_user_check - wrappers don't want to async work
async def log_input_image_data(message, input_image_name):
    await exist_user_check(message)
    await create_image_entry(message.from_user.id, input_image_name)


async def log_output_image_data(message, input_image_name, output_image_names):
    await exist_user_check(message)
    await update_image_entry(message.from_user.id, input_image_name, output_image_names)


async def run_sync_db_operation(operation):
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            operation(session)
            await session.commit()


async def fetch_user_data(user_id):
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


async def format_userdata_output(user, messages):
    image_names_dict = await fetch_image_names_by_user_id(user.user_id)
    if image_names_dict:
        image_names = [f"original: {input_image} "
                       f"output [{len(output_images.split(',')) if output_images else 0} img]:"
                       f"{output_images})" for input_image, output_images in image_names_dict.items()]
        image_names = '\n\t\t\t'.join(image_names)
        print(f"\nUser: {user.username} (ID:{user.user_id} Name: {user.first_name} {user.last_name})"
              f"\n\tMode: {user.mode}"
              f"\n\tStatus: {user.status}"
              f"\n\tImages used: {len(image_names_dict.values()) + len(image_names_dict.keys())} "
              f"left: {user.requests_left}"
              f"\n\tMessages: [{messages}]"
              f"\n\tImages: [{image_names}]")
    else:
        print(f"User: {user.username}, Messages: [{messages}], Images: []")


async def return_user(user):

    return {'user_id': user.user_id, 'username': user.username, 'first_name': user.first_name,
            'last_name': user.last_name, 'mode': user.mode, 'status': user.status,
            'requests_left': user.requests_left}


async def fetch_all_user_ids():
    async with AsyncSession(async_engine) as session:
        result = await session.execute(select(User.user_id))
        user_ids = result.scalars().all()
        return user_ids


async def fetch_all_users_data():
    all_user_ids = await fetch_all_user_ids()
    for user_id in all_user_ids:
        await fetch_user_data(user_id)


async def update_photo_timestamp(user_id, timestamp):
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()
            if user:
                user.last_photo_sent_timestamp = timestamp
            await session.commit()


async def example_usage():
    class UserI:
        def __init__(self, id_, username=None, first_name=None, last_name=None):
            self.id = id_
            self.username = username
            self.first_name = first_name
            self.last_name = last_name

    class MessageI:
        def __init__(self, user_id, from_user=None):
            self.user_id = user_id
            self.from_user = from_user

    from_user_info = UserI(id_=12345, username='testuser1', first_name='Test1', last_name='User1')
    message = MessageI(user_id=12345, from_user=from_user_info)

    await initialize_database()
    await insert_user(12345, 'user1', 'User', 'One', mode=1)
    await insert_user(67890, 'user2', 'User', 'Two', mode=2)
    await insert_user(54321, 'user3', 'User', 'Three', mode=1)
    await log_input_image_data(message, "input1.jpg")
    await log_input_image_data(message, "input2.jpg")
    await update_user_mode(12345, mode=3)

    # Fetch and print user data
    await fetch_user_data(12345)
    await fetch_user_data(67890)
    await fetch_user_data(54321)
    await fetch_all_users_data()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
