import aiohttp
import io
import random
import os
import yaml

from aiogram import F
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, Message
from face_extraction.extract_face import get_face
from PIL import Image
# from fastapi import FastAPI, UploadFile, File
# from bot.user_logger import log_user


def get_contacts():
    with open('bot/contacts.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config['telegram'], config['github']


def generate_filename():
    while True:
        filename = f'img_{random.randint(1, 999999)}.png'
        if not os.path.exists(filename):
            return filename


async def handle_start(message):
    await message.answer("Welcome! Send me a photo, and I'll process it.")


async def handle_contacts(message):
    tg, git = get_contacts()
    await message.answer(f"You can reach to me through\nTelegram: @{tg}\nGithub: {git}")


async def handle_help(message):
    help_message = (
        "This bot can only process photos. Here are the available commands:\n"
        "/start - Start the bot\n"
        "/help - Display this help message\n"
        "Send me a photo, and I'll process it!"
    )
    await message.answer(help_message)


def get_token():
    with open('../config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config['token']


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


async def alternative_handle_image(message: Message, token):
    #  face_processed_url = 'http://localhost:8000/images/'
    face_extraction_url = 'http://localhost:8000/extract_face'
    #  file_id = message.photo[-1].file_id
    file_path = await message.bot.get_file(message.photo[-1].file_id)
    file_url = f"https://api.telegram.org/file/bot{token}/{file_path.file_path}"
    output = generate_filename()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    print('Image downloaded')
                    content = await response.read()
                else:
                    error_message = await response.text()
                    print(error_message)
                    await message.answer('Failed to download image. Please try again')
                    return
            dataform = aiohttp.FormData()   # TODO: find the bug
            dataform.add_field('file', content, filename='image.jpg', content_type='image/jpeg')
            async with session.post(face_extraction_url, data=dataform) as response:
                # {'file':('image.jpg', content, 'image/jpeg')}) as response:
                print('Sending image through fastapi')
                if response.status == 200:
                    image_data = await response.read()

                    imgfile = Image.open(io.BytesIO(image_data))
                    imgfile.save(output, format='PNG')

                    inp_file = FSInputFile(output)
                    await message.answer_photo(photo=inp_file)

                    os.remove(output)
                    print('Image sent')
                else:
                    error_message = await response.text()
                    print(error_message)
                    await message.answer('Failed to process image. Please try again')
                    return

    except Exception as e:
        print(e)    # TODO: log it
        await message.answer('Sorry must have been an error. Try again later.')


def setup_handlers(dp, bot_token):

    dp.message(Command('start'))(handle_start)
    dp.message(Command('help'))(handle_help)
    dp.message(Command('contacts'))(handle_contacts)

    async def image_handler(message: Message):
        await alternative_handle_image(message, bot_token)
    dp.message(F.photo)(image_handler)
    # dp.message(F.photo)(lambda message: alternative_handle_image(message, bot_token))
