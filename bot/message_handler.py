import aiohttp
import io
import json
import random
import os
import yaml

from datetime import datetime, timedelta
from aiogram import F
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from PIL import Image
from bot.db_requests import set_requests_left, update_user_mode, log_input_image_data, exist_user_check, \
                            log_output_image_data, log_text_data, fetch_user_data, fetch_all_users_data, \
                            decrement_requests_left, buy_premium, update_photo_timestamp, receive_user, \
                            toggle_receive_target_flag


def load_target_names():
    with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '\\target_images.json', 'r') as file:
        return json.load(file)


targets = load_target_names()
preloaded_collages = {category: FSInputFile(collage_path) for category, collage_path in targets['collages'].items()}
FACE_EXTRACTION_URL = 'http://localhost:8000/swapper'
DELAY_BETWEEN_IMAGES = 2
SENT_TIME = {}


async def get_contacts():
    with open('bot/contacts.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config


async def generate_filename(folder='original'):
    while True:
        filename = os.path.join('temp/'+folder, f'img_{random.randint(100, 999999)}.png')
        if not os.path.exists(filename):
            return os.path.join(os.getcwd(), filename)


async def handle_start(message):
    await exist_user_check(message)
    await message.answer("Welcome! Send me a photo of a person and I will return their face.")
    await handle_category_command(message)


async def handle_support(message):
    user = f'ids:{message.id} @{message.username} {message.url}\n' \
           f'name: {message.first_name} {message.last_name} {message.full_name}'
    contact = await get_contacts()
    await message.bot.send_message(contact['my_id'], f'User: {user} requires help')
    await message.answer("Request has been sent to the administrator. You'll be contacted. Probably")


async def handle_contacts(message):
    contacts = await get_contacts()
    await message.answer(f"Reach me out through:\nTelegram: @{contacts['telegram']}\nGithub: {contacts['github']}\n")


async def donate_link(message):
    bthash = await get_contacts()
    response_message = "Support me with BTC:"
    await message.answer(response_message)
    await message.answer(bthash['cryptohash'])


async def handle_help(message):
    help_message = (
        "This bot can only process photos that have people on it. Here are the available commands:\n"
        "/start - Start the bot\n"
        "/help - Display this help message\n"
        "/status - Check your account limits\n"
        "/select - Select a category of pictures\n"
        "/reset_limit - Reset your image limit to 10\n"
        "/buy_premium - Add 100 images and set account to premium\n"
        "/custom_target - Premium option to add your target image\n"  # TODO: set limits to 10
        "/contacts - Show contacts list\n"
        "/support - Send a support request\n"
        "/donate - Support me\n"
        "Send me a photo, and I'll process it!")
    await message.answer(help_message)


async def save_img(img, img_path):
    orig = Image.open(io.BytesIO(img))
    orig.save(img_path, format='PNG')


async def check_limit(user, message):
    if user.requests_left <= 0:
        await message.answer("Sorry, you are out of attempts. Try again later")
        return False
    return True


async def check_time_limit(user, message, n_time=20):
    if user.status == 'premium':
        return True
    if (datetime.now() - user.last_photo_sent_timestamp) < timedelta(seconds=n_time):
        secs = (datetime.now() - user.last_photo_sent_timestamp).total_seconds()
        text = f"Sorry, too many requests. Please wait {n_time-int(secs)} more seconds"
        await message.answer(text)
        return False
    return True


async def prevent_multisending(message):
    dt = datetime.now()
    last_sent = SENT_TIME.get(message.from_user.id, None)
    if message.media_group_id is None and (last_sent is None or (
            dt - last_sent).total_seconds() >= DELAY_BETWEEN_IMAGES):
        SENT_TIME[message.from_user.id] = dt
        return True
    return False


async def handle_image(message: Message, token):
    await exist_user_check(message)
    user = await fetch_user_data(message.from_user.id)
    if not (await check_limit(user, message) and await check_time_limit(user, message)):
        return
    await update_photo_timestamp(user.user_id, datetime.now())

    file_path = await message.bot.get_file(message.photo[-1].file_id)
    file_url = f"https://api.telegram.org/file/bot{token}/{file_path.file_path}"
    input_path = await generate_filename('target_images' if user.receive_target_flag else 'original')
    await log_input_image_data(message, input_path)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    print('Image downloaded')
                    await message.answer('Image received. Processing...')
                    content = await response.read()
                    await save_img(content, input_path)
                    if await target_image_check(user, input_path):
                        await message.answer('Target image uploaded, send your source image')
                        return
                else:
                    error_message = await response.text()
                    print(error_message)
                    await message.answer('Failed to download image. Please try again')
                    return

            async with session.post(FACE_EXTRACTION_URL,
                                    data={'file_path': input_path,
                                          'mode': user.mode}
                                    ) as response:
                print('Sending image path through fastapi')

                if response.status == 200:
                    image_data_list = await response.text()
                    image_paths = json.loads(image_data_list)
                    await log_output_image_data(message, input_path, image_paths)   # logging to db

                    for output_path in image_paths:
                        user = await fetch_user_data(message.from_user.id)
                        if not (await check_limit(user, message)):
                            return
                        inp_file = FSInputFile(output_path)
                        await message.answer_photo(photo=inp_file)
                        print('Image sent')

                    await decrement_requests_left(user.user_id, n=len(image_paths))
                    limit = max(0, user.requests_left - len(image_paths))
                    await message.answer(f'You have {limit} attempts left')

                else:
                    error_message = await response.text()
                    print(error_message)
                    await message.answer('Failed to process image. Please try again')
                    return

    except Exception as e:
        print(e)    # TODO: log it
        await message.answer('Sorry must have been an error. Try again later.')


async def handle_text(message: Message):
    await exist_user_check(message)
    await log_text_data(message)
    response_text = (
        "I'm currently set up to process photos only. "
        "Please send me a photo of a person, and I will return their face.")
    await fetch_user_data(message.from_user.id)
    await message.answer(response_text)


async def handle_unsupported_content(message: Message):
    await message.answer("Sorry, I can't handle this type of content.\n"
                         "Please send me a photo from your gallery, and I will return the face of a person on it.")


async def output_all_users_to_console(*args):
    await fetch_all_users_data()


async def set_user_to_premium(message):
    await exist_user_check(message)
    await buy_premium(message.from_user.id)
    new_number = await fetch_user_data(message.from_user.id)
    await message.answer(f'Congratulations! You got premium status!'
                         f'\nYou have {new_number.requests_left} attempts left')


async def reset_images_left(message):
    await exist_user_check(message)
    n = 10
    await set_requests_left(message.from_user.id, n)
    new_number = await fetch_user_data(message.from_user.id)
    await message.answer(f'You have {new_number.requests_left} attempts left')


async def check_status(message):
    await exist_user_check(message)
    user = await fetch_user_data(message.from_user.id)
    await message.answer(f'Your have a {user.status} account\nYou have {user.requests_left} attempts left')


async def target_image_check(user, input_image):
    if user.status == 'premium' and user.receive_target_flag:
        await update_user_mode(user.user_id, input_image)
        await toggle_receive_target_flag(user.user_id)
        return input_image


async def set_receive_flag(message):
    await exist_user_check(message)
    user = await receive_user(message.from_user.id)
    if user.status == 'premium':
        await toggle_receive_target_flag(message.from_user.id, 1)
        await message.answer('Changing set to receiving a new target.\nSend target image.')
        return
    await message.answer('You need to be a premium user for that. Use /buy_premium function')


async def handle_category_command(message: Message):
    keyboard = await create_category_buttons()
    await message.answer("Choose your target category:", reply_markup=keyboard)


async def create_category_buttons():
    row, keyboard_buttons = [], []
    for category in targets['categories']:
        text = category.capitalize()
        data = f'c_{category}'
        row.append(InlineKeyboardButton(text=text, callback_data=data))
        if len(row) == 2:
            keyboard_buttons.append(row)
            row = []
    if row:
        keyboard_buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


async def show_category_collage(query, category):
    await query.message.answer_photo(photo=preloaded_collages[category])


async def show_images_for_category(query: CallbackQuery, category: str):
    await show_category_collage(query, category)
    buttons = [[InlineKeyboardButton(text=item["name"], callback_data=item['mode']) for item in chunk]
               for chunk in chunk_list(targets['categories'].get(category, []), 2)]
    back_button = InlineKeyboardButton(text="Back", callback_data="back")
    buttons.append([back_button])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await query.message.edit_text(f"Choose an image from {category.title()}:", reply_markup=keyboard)


def chunk_list(data, size):
    for i in range(0, len(data), size):
        yield data[i:i + size]


async def process_image_selection(query: CallbackQuery):
    user_id = query.from_user.id
    data = query.data
    await toggle_receive_target_flag(user_id)
    await update_user_mode(user_id, data)
    await query.message.answer("Target image selected\nSend me a photo, and I'll process it!")
    await fetch_user_data(user_id)
    await query.answer()


def setup_handlers(dp, bot_token):
    dp.message(Command('start'))(handle_start)
    dp.message(Command('help'))(handle_help)
    dp.message(Command('contacts'))(handle_contacts)
    dp.message(Command('support'))(handle_support)
    dp.message(Command('show_users'))(output_all_users_to_console)
    dp.message(Command('custom_target'))(set_receive_flag)
    dp.message(Command('buy_premium'))(set_user_to_premium)
    dp.message(Command('reset_limit'))(reset_images_left)
    dp.message(Command('status'))(check_status)
    dp.message(Command('donate'))(donate_link)
    dp.message(Command('select'))(handle_category_command)
    dp.callback_query()(button_callback_handler)

    async def image_handler(message: Message):
        if await prevent_multisending(message):
            await handle_image(message, bot_token)
            return
        await message.answer("Please send one photo at a time.")

    dp.message(F.photo)(image_handler)
    dp.message(F.text)(handle_text)
    dp.message(F.sticker | F.video | F.document | F.location | F.poll | F.audio | F.voice | F.contact | F.video_note)(
               handle_unsupported_content)


async def button_callback_handler(query: CallbackQuery):
    if query.data.startswith('c_'):  # Check if the callback data starts with 'c_'
        category = query.data.split('_')[1]
        await show_images_for_category(query, category)
    elif query.data == 'back':
        keyboard = await create_category_buttons()
        await query.message.edit_text("Choose your target category:", reply_markup=keyboard)
    else:
        await process_image_selection(query)
    await query.answer()
