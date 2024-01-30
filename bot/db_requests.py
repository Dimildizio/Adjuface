import logging
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, func
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload


DATABASE_FILE = 'user_database.db'
ASYNC_DB_URL = f'sqlite+aiosqlite:///{DATABASE_FILE}'

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
                existing_user.mode = mode
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


async def insert_message(user_id, text_data):
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            user = await session.execute(select(User).filter_by(user_id=user_id))
            user = user.scalar_one_or_none()

            if user:
                message = Message(user_id=user.id, text_data=text_data)
                session.add(message)
            print('MEGAMESSAGE', message)
            await session.commit()


async def insert_image_name(user_id, input_image_name, output_image_names):

    async with AsyncSession(async_engine) as session:
        async with session.begin():
            existing_entry = await session.execute(select(ImageName).filter_by(
                                    user_id=user_id, input_image_name=input_image_name))
            existing_entry = existing_entry.scalar_one_or_none()

            str_outputs = ','.join(output_image_names) if output_image_names else None
            if existing_entry:
                existing_entry.output_image_names = str_outputs
                print("CHANGING OUTPUT", existing_entry.output_image_names)
            else:
                # Create a new entry
                new_entry = ImageName(user_id=user_id, input_image_name=input_image_name,
                                      output_image_names=str_outputs)
                session.add(new_entry)
            #await fetch_user_data(user_id)
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
    await insert_message(message.from_user.id, message.text)


# exist_user_check - wrappers don't want to async work
async def log_input_image_data(message, input_image_name):
    await exist_user_check(message)
    await insert_image_name(message.from_user.id, input_image_name, None)


async def log_output_image_data(message, input_image_name, output_image_names):
    #await exist_user_check(message)
    #  for output_image_name in output_image_names:
    await insert_image_name(message.from_user.id, input_image_name, output_image_names)


async def run_sync_db_operation(operation):
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            operation(session)
            await session.commit()


async def fetch_user_data(user_id):
    async with AsyncSession(async_engine) as session:
        result = await session.execute(
            select(User).where(User.user_id == user_id).options(selectinload(User.messages),
                                                                selectinload(User.image_names))
        )
        user = result.scalar_one_or_none()
        if user:
            messages = ', '.join([message.text_data for message in user.messages])
            # Iterate through image names and print each one
            image_names = [f"{image_name.input_image_name} ({image_name.output_image_names})"
                           for image_name in user.image_names]
            print('WE ARE IMG NAMES', image_names)
            image_names = ', '.join(image_names)
            print(f"User: {user.username}, Messages: [{messages}], Images: [{image_names}]")
        else:
            print("User not found")

async def test_main():
    await initialize_database()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARN)
    await insert_user(user_id=12345, username='testuser1', first_name='Test1', last_name='User1', mode=1)
    await insert_message(user_id=12345, text_data='Hello, World 1!')
    await insert_image_name(user_id=12345, input_image_name='input1.jpg',
                            output_image_names='output1_1.jpg,output1_2.jpg')

    await insert_user(user_id=67890, username='testuser2', first_name='Test2', last_name='User2', mode=2)
    await insert_message(user_id=67890, text_data='Hello, World 2!')
    await insert_image_name(user_id=67890, input_image_name='input2.jpg',
                            output_image_names='output2_1.jpg,output2_2.jpg')

    await fetch_user_data(12345)
    await fetch_user_data(67890)
    await update_user_mode(12345, 3)

    await insert_user(user_id=54321, username='testuser3', first_name='Test3', last_name='User3', mode=1)
    await insert_message(user_id=54321, text_data='Hello, World 3!')
    await insert_image_name(user_id=54321, input_image_name='input3.jpg',
                            output_image_names='output3_1.jpg,output3_2.jpg')
    # Fetch and print all data again to see the changes
    await fetch_user_data(12345)
    await fetch_user_data(67890)
    await fetch_user_data(54321)

# if __name__ == "__main__":
#    asyncio.run(test_main())
