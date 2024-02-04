import pytest
import asyncio
import os
from bot.db_requests import insert_user, fetch_user_data, initialize_database, Base, User, Message, log_input_image_data,\
    ImageName, fetch_all_users_data, update_user_mode
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_FILE_TEST = 'test_user_database.db'
ASYNC_DB_URL_TEST = f'sqlite+aiosqlite:///{DATABASE_FILE_TEST}'

async_engine = create_async_engine(ASYNC_DB_URL_TEST, echo=True)



@pytest.fixture(scope="module")
async def setup_database():
    async with async_engine.begin() as conn:
        # Drop all tables to ensure a clean state, then create all tables
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Optional: Cleanup after tests
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def db_engine():
    engine = create_async_engine(ASYNC_DB_URL_TEST, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async_session = sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


async def create_test_data(db_session):
    # Create test data for the test
    await insert_user(12345, 'user1', 'User', 'One', mode=1)
    await insert_user(67890, 'user2', 'User', 'Two', mode=2)
    await insert_user(54321, 'user3', 'User', 'Three', mode=1)

async def test_insert_and_fetch_user(db_session):
    await create_test_data(db_session)

    user_id = 12345
    username = "testuser1"
    first_name = "Test1"
    last_name = "User1"

    await insert_user(user_id, username, first_name, last_name, mode=1)
    user_data = await fetch_user_data(user_id)
    assert user_data is not None
    assert user_data.username == username
    assert user_data.first_name == first_name
    assert user_data.last_name == last_name

async def test_fetch_all_users(db_session):
    await create_test_data(db_session)
    await fetch_all_users_data()


async def test_example():
    from_user_info = User(id_=12345, username='testuser1', first_name='Test1', last_name='User1')
    message = Message(user_id=12345, from_user=from_user_info)

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

    asyncio.run(initialize_database())
    asyncio.run(test_example)
    asyncio.run(pytest.main(["-v"]))
    os.remove(DATABASE_FILE_TEST)
