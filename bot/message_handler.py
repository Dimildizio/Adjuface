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
    return config


def generate_filename(folder='original'):
    while True:
        filename = os.path.join('temp/'+folder, f'img_{random.randint(1, 999999)}.png')
        if not os.path.exists(filename):
            return filename


async def handle_start(message):
    await message.answer("Welcome! Send me a photo of a person and I will return their face.")


async def handle_support(message):
    m = message.from_user
    print(dir(m))
    text = f'user requires help:\nids:{m.id} @{m.username} {m.url}\nname: {m.first_name} {m.last_name} {m.full_name}'
    await message.bot.send_message(get_contacts()['my_id'], f'{text} requires help')
    await message.answer("Request has been sent to the administrator. You'll be contacted. Probably")


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


async def handle_image(message: Message, token):
    #  face_processed_url = 'http://localhost:8000/images/'
    face_extraction_url = 'http://localhost:8000/extract_face'
    #  file_id = message.photo[-1].file_id
    file_path = await message.bot.get_file(message.photo[-1].file_id)
    file_url = f"https://api.telegram.org/file/bot{token}/{file_path.file_path}"
    output = generate_filename('result')

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
            dataform = aiohttp.FormData()
            dataform.add_field('file', content, filename='image.png', content_type='image/png')
            async with session.post(face_extraction_url, data=dataform) as response:
                # {'file':('image.jpg', content, 'image/jpeg')}) as response:
                print('Sending image through fastapi')
                if response.status == 200:
                    image_data = await response.read()

                    orig = Image.open(io.BytesIO(content))
                    orig.save(generate_filename(), format='PNG')

                    imgfile = Image.open(io.BytesIO(image_data))
                    imgfile.save(output, format='PNG')

                    inp_file = FSInputFile(output)
                    await message.answer_photo(photo=inp_file)

                    #os.remove(output)
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
    response_text = (
        "I'm currently set up to process photos only. "
        "Please send me a photo of a person, and I will return their face.")
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
