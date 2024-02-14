import io
import os
import json
import random
import yaml


from datetime import datetime, timedelta
from PIL import Image
from sqlalchemy import Table, Column, Integer, String, TIMESTAMP, MetaData, func, text
from sqlalchemy.ext.asyncio import create_async_engine
from typing import Tuple, Dict


def list_project_structure(path: str, to_ignore: Tuple[str, ...] = ('temp', '__pycache__', 'research'),
                           indent: int = 0) -> None:
    """
    Lists the project directory structure, ignoring specified directories.

    :param path: The path to the directory to list.
    :param to_ignore: A list of directory names to ignore.
    :param indent: The indentation level for printing the directory structure.
    """
    if os.path.isdir(path):
        folder_name = os.path.basename(path)
        if folder_name not in to_ignore and not folder_name.startswith('.'):
            print(' ' * indent + '-' + folder_name)
            for item in os.listdir(path):
                new_path = os.path.join(path, item)
                list_project_structure(new_path, to_ignore, indent + 4)
    else:
        file_name = os.path.basename(path)
        if not file_name.startswith('.'):
            print(' ' * indent + '-' + file_name)


async def remove_old_image(paths=('temp\\result', 'temp\\original', 'temp\\target_images'),
                           hour_delay: int = 48, name_start: str = 'img'):
    """
    Removes images that are older than a specified time delay and start with a specified name from a folders.

    :param paths: The names of the folders to parse.
    :param hour_delay: The age threshold in hours for deleting an image.
    :param name_start: The prefix of the image filenames to consider for deletion.
    :return: None
    """
    now = datetime.now()
    time_threshold = timedelta(hours=hour_delay)
    for folder_path in paths:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(os.getcwd(), folder_path, filename)
            if filename.startswith(name_start) and os.path.isfile(file_path):
                file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if now - file_creation_time > time_threshold:
                    os.remove(file_path)
                    print(f"Deleted: {file_path} - {file_creation_time}")


async def add_scheduler_logs_table() -> None:
    """"Migrate db creating a new scheduler logs table"""
    from bot.db_requests import async_engine
    metadata = MetaData()
    scheduler_logs_table = Table(
        'scheduler_logs', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('job_name', String, nullable=False),
        Column('run_datetime', TIMESTAMP, server_default=func.now()),
        Column('status', String, nullable=False),
        Column('details', String, nullable=True))

    async with async_engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    print(scheduler_logs_table)


async def list_tables(db_url: str = 'sqlite+aiosqlite:///users_database.db') -> None:
    engine = create_async_engine(db_url, echo=True)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = result.fetchall()
        print("Tables in the database:")
        for table in tables:
            print(table[0])


def scheduler_logs_dag() -> None:
    """Test func to check scheduler table entries"""
    import asyncio
    from bot.db_requests import fetch_scheduler_logs
    asyncio.run(fetch_scheduler_logs())


def get_yaml(filename='bot/contacts.yaml') -> Dict[str, str]:
    """
    Get info from a YAML file.

    :return: A dictionary containing information.
    """
    with open(filename, 'r') as f:
        config = yaml.safe_load(f)
    return config


def get_localization(filename: str = 'localization.json', lang='ru') -> Dict[str, str]:
    """
    Get info from a json file.

    :return: A dictionary containing information.
    """
    with open(filename, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config[lang]


def load_target_names(lang: str = 'en') -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Load target names from a JSON file.

    :return: A dictionary containing target names.
    """
    with open(f'target_images_{lang}.json', 'r', encoding='utf-8') as file:
        return json.load(file)


async def generate_filename(folder: str = 'original') -> str:
    """
    Asynchronously generates a unique filename for storing an image in a specified folder.

    :param folder: The name of the folder within 'temp' (custom targets or original imgs) where the file will be stored.
    :return: The absolute path to the generated filename.
    """
    while True:
        filename = os.path.join('temp/'+folder, f'img_{random.randint(100, 999999)}.png')
        if not os.path.exists(filename):
            return os.path.join(os.getcwd(), filename)


def chunk_list(data: list, size: int):
    """
    Splits a list into chunks of a specified size.

    :param data: The list to split into chunks.
    :param size: The size of each chunk.
    :return: A generator yielding chunks of the list.
    """
    for i in range(0, len(data), size):
        yield data[i:i + size]


async def save_img(img: bytes, img_path: str) -> None:
    """
    Saves an image from a byte stream to a specified path.

    :param img: The image data in bytes.
    :param img_path: The file path where the image will be saved.
    :return: None
    """
    orig = Image.open(io.BytesIO(img))
    orig.save(img_path, format='PNG')


if __name__ == "__main__":
    scheduler_logs_dag()
