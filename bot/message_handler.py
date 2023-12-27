from aiogram import F
from aiogram.filters.command import Command
from aiogram.types import FSInputFile
# from bot.user_logger import log_user
import os
from face_extraction.extract_face import get_face


async def handle_start(message):
    await message.answer("Welcome! Send me a photo, and I'll process it.")


async def handle_help(message):
    help_message = (
        "This bot can only process photos. Here are the available commands:\n"
        "/start - Start the bot\n"
        "/help - Display this help message\n"
        "Send me a photo, and I'll process it!"
    )
    await message.answer(help_message)


async def handle_image(message):
    try:
        print(os.getcwd())
        temp_dir = "temp"
        os.makedirs(temp_dir, exist_ok=True)

        temp_file = f"{temp_dir}/{message.photo[-1].file_id}.jpg"
        new_file = f"{temp_dir}/{message.photo[-1].file_id}_modified.jpg"

        await message.bot.download(message.photo[-1], destination=temp_file)
        await get_face(temp_file, new_file)

        await message.answer_photo(FSInputFile(new_file), caption="Here is your processed image")
    except Exception as e:
        print(e)    # TODO: log it
        message.answer('Sorry must have been an error. Try again later.')


def setup_handlers(dp):
    dp.message(Command('start'))(handle_start)
    dp.message(Command('help'))(handle_help)
    dp.message(F.photo)(handle_image)
