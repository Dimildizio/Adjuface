import aiohttp
import io
import json
import random
import os
import yaml

from aiogram import F
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, Message
from PIL import Image
from bot.db_handler import log_user_info, fetch_user_data


def get_contacts():
    with open('bot/contacts.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config


def generate_filename(folder='original'):
    while True:
        filename = os.path.join('temp/'+folder, f'img_{random.randint(1, 999999)}.png')
        if not os.path.exists(filename):
            return filename


def get_n_name(name, n):
    return f'{name[:-4]}_{n}.png'


async def handle_start(message):
    await message.answer("Welcome! Send me a photo of a person and I will return their face.")


async def handle_support(message):
    user = await user_contacts(message.from_user)
    await message.bot.send_message(get_contacts()['my_id'], f'User: {user} requires help')
    await message.answer("Request has been sent to the administrator. You'll be contacted. Probably")


async def user_contacts(m):
    return f'ids:{m.id} @{m.username} {m.url}\nname: {m.first_name} {m.last_name} {m.full_name}'


async def handle_contacts(message):
    contacts = get_contacts()
    await message.answer(f"Reach me out through:\nTelegram: @{contacts['telegram']}\nGithub: {contacts['github']}\n")


async def handle_help(message):
    help_message = (
        "This bot can only process photos that have people on it. Here are the available commands:\n"
        "/start - Start the bot\n"
        "/help - Display this help message\n"
        "/contacts - Show contacts list\n"
        "/support - send a support request\n"
        "Send me a photo, and I'll process it!")
    await message.answer(help_message)


async def save_img(img, img_path):
    orig = Image.open(io.BytesIO(img))
    orig.save(img_path, format='PNG')


async def handle_image(message: Message, token):
    face_extraction_url = 'http://localhost:8000/insighter'
    file_path = await message.bot.get_file(message.photo[-1].file_id)
    file_url = f"https://api.telegram.org/file/bot{token}/{file_path.file_path}"
    input_path = generate_filename()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    print('Image downloaded')
                    content = await response.read()
                    await save_img(content, input_path)
                else:
                    error_message = await response.text()
                    print(error_message)
                    await message.answer('Failed to download image. Please try again')
                    return

            async with session.post(face_extraction_url, data={'file_path': os.path.join(
                                                                os.getcwd(), input_path)}) as response:
                print('Sending image path through fastapi')

                if response.status == 200:
                    image_data_list = await response.text()
                    image_paths = json.loads(image_data_list)
                    await log_user_info(message, 'image', input_path, image_paths)  # logging

                    for output_path in image_paths:
                        inp_file = FSInputFile(output_path)
                        await message.answer_photo(photo=inp_file)
                        print('Image sent')

                else:
                    error_message = await response.text()
                    print(error_message)
                    await message.answer('Failed to process image. Please try again')
                    return

    except Exception as e:
        print(e)    # TODO: log it
        await message.answer('Sorry must have been an error. Try again later.')


async def handle_text(message: Message):
    await log_user_info(message, 'text')
    response_text = (
        "I'm currently set up to process photos only. "
        "Please send me a photo of a person, and I will return their face.")
    await fetch_user_data(message.from_user.id)
    await message.answer(response_text)


def setup_handlers(dp, bot_token):
    dp.message(Command('start'))(handle_start)
    dp.message(Command('help'))(handle_help)
    dp.message(Command('contacts'))(handle_contacts)
    dp.message(Command('support'))(handle_support)

    async def image_handler(message: Message):
        await handle_image(message, bot_token)
    dp.message(F.photo)(image_handler)
    dp.message(F.text)(handle_text)
