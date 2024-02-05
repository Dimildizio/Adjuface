"""
This module, leveraging the asyncio library, FastAPI, Aiogram, and various image processing libraries,
offers a sophisticated face-swapping bot capable of handling image-based requests via a Telegram bot interface.
The bot utilizes advanced face detection and swapping algorithms to process user-submitted photos, enabling the dynamic
replacement of faces in images with those from a predefined set of target images or user-provided content for
premium accounts.

Key Features:
- Asynchronous handling of image processing and Telegram bot interactions for efficient operation under load.
- Integration with FastAPI for serving a REST API that facilitates face extraction and swapping operations.
- Utilization of the Aiogram library for Telegram bot development, supporting commands, text, and photo messages.
- Preloading of target images and categories from JSON, allowing for easy extension of the bot's capabilities.
- Support for premium user features, including custom target face uploads and increased processing limits.
- Implementation of rate limiting and request tracking to manage demand and ensure equitable resource usage.
- Provision of user support and contact information through the bot interface, enhancing user engagement.

Usage:
- Deploy the bot and interact with it via Telegram. Users can send commands to start interactions, upload photos for
  face swapping, or inquire about their usage limits. Premium features are unlocked through specific commands.

Dependencies:
- aiohttp: For asynchronous HTTP requests within the face-swapping REST API.
- Pillow (PIL): For image manipulation tasks, including reading, writing, and transforming images.
- Aiogram: For creating and managing the Telegram bot interface, handling user commands, and processing messages.
- YAML: For loading configuration data, such as contact information.
- OpenCV (cv2): Optionally used for additional image processing capabilities.


Configuration:
- Before deployment, configure the database, target images, categories, and contact information in JSON and YAML files.
  Adjust the REST API endpoint as needed to match the deployment environment.

Note:
- This module is designed to be modular and extensible, allowing for the addition of new features and improvements
  in face detection and swapping algorithms. Ensure that all dependencies are installed and the bot token is
  securely managed.
  - TODO: The file is too large. Refacrtoring required and splitting it into several smaller funcs and .py files
  - TODO: add autodeletion of custom target, original and result files that are older than a day every midnight

Example:
    Deploy the bot and interact with it through Telegram. Use commands like /start, /help, and /donate ;) to navigate
    the bot's features. Send a photo to the bot, and it will process it according to the selected target face or
    category.
"""


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
                            decrement_requests_left, buy_premium, update_photo_timestamp, fetch_user_by_id, \
                            toggle_receive_target_flag, decrement_targets_left, clear_output_images_by_user_id
from typing import Dict, Any, Optional


def load_target_names() -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Load target names from a JSON file.

    :return: A dictionary containing target names.
    """
    with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '\\target_images.json', 'r') as file:
        return json.load(file)


def get_contacts() -> Dict[str, str]:
    """
    Get contacts from a YAML file.

    :return: A dictionary containing contact information.
    """
    with open('bot/contacts.yaml', 'r') as f:
        config = yaml.safe_load(f)
    return config


# Define constants
TARGETS = load_target_names()
PRELOADED_COLLAGES = {category: FSInputFile(collage_path) for category, collage_path in TARGETS['collages'].items()}
CONTACTS: Dict[str, str] = get_contacts()

FACE_EXTRACTION_URL = 'http://localhost:8000/swapper'
TGBOT_PATH = 'https://api.telegram.org/file/bot'

DELAY_BETWEEN_IMAGES = 2
SENT_TIME = {}   # dictionary with user IDs and timestamps


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


async def handle_start(message: Message) -> None:
    """
    Handles the start command from a user by checking their existence, sending a welcome message,
    and prompting for a photo.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message)
    welcome = "Welcome! Send me a photo of a person and I will return their face.\n\n" \
           "For video instruction visit:\nhttps://youtu.be/01Qah4aU_rE"

    await message.answer_photo(photo=PRELOADED_COLLAGES['instruction'], caption=welcome)
    await handle_category_command(message)


async def handle_support(message: Message) -> None:
    """
    Handles a support request from a user by sending their information to the administrator and
    notifying the user that their request has been forwarded. However, so far sends user id, not the link to account.

    :param message: The message with user data.
    :return: None
    """
    m = message.from_user
    user = f'ids:{m.id} @{m.username} {m.url}\nname: {m.first_name} {m.last_name} {m.full_name}'
    await message.bot.send_message(CONTACTS['my_id'], f'User: {user} requires help')
    await message.answer("Request has been sent to the administrator. You'll be contacted. Probably")


async def handle_contacts(message) -> None:
    """
    Sends the contact information to user.

    :param message: The user data message.
    :return: None
    """
    #                                          f"\nGithub: {CONTACTS['github']}\n")
    await message.answer(f"Reach me out through:\nTelegram: @{CONTACTS['telegram']}")


async def donate_link(message) -> None:
    """
    Sends a message to the user with information on how to support via cryptocurrency.

    :param message: User data message.
    :return: None
    """
    response_message = "Support me with BTC:"
    await message.answer(response_message)
    await message.answer(CONTACTS['cryptohash'])


async def handle_help(message: Message) -> None:
    """
    Sends a help message to the user with available commands.

    :param message: The user data message from the user.
    :return: None
    """
    help_message = (
        "This bot can only process photos that have people on it. Here are the available commands:\n"
        "/start - Start the bot\n"
        "/help - Display this help message\n"
        "/status - Check your account limits\n"
        "/select - Select a category of pictures\n"
        "/reset_user - (Debug): Reset your status and set image limit to 10\n"
        "/buy_premium - Add 100 images and set account to premium\n"
        "/custom_target - Premium option to add your target image\n"
        "/contacts - Show contacts list\n"
        "/support - Send a support request\n"
        "/donate - Support me\n"
        "Send me a photo, and I'll process it!")
    await message.answer(help_message)


async def save_img(img: bytes, img_path: str) -> None:
    """
    Saves an image from a byte stream to a specified path.

    :param img: The image data in bytes.
    :param img_path: The file path where the image will be saved.
    :return: None
    """
    orig = Image.open(io.BytesIO(img))
    orig.save(img_path, format='PNG')


async def check_limit(user: Any, message: Message) -> bool:
    """
    Checks if the user has reached their request limit.

    :param user: The user class object.
    :param message: The user data message from the user.
    :return: True if the user has requests left, False otherwise.
    """
    if user.requests_left <= 0:
        await message.answer("Sorry, you are out of attempts. Try again later")
        return False
    return True


async def check_time_limit(user: Any, message: Message, n_time: int = 20) -> bool:
    """
    Checks if a user has reached a time limit for an action.

    :param user: The user class object.
    :param message: The message obj.
    :param n_time: The time limit in seconds (default is 20).
    :return: True if the user is within the time limit, False otherwise.
    """
    if user.status == 'premium':
        return True
    if (datetime.now() - user.last_photo_sent_timestamp) < timedelta(seconds=n_time):
        secs = (datetime.now() - user.last_photo_sent_timestamp).total_seconds()
        text = f"Sorry, too many requests. Please wait {n_time-int(secs)} more seconds"
        await message.answer(text)
        return False
    return True


async def prevent_multisending(message: Message) -> bool:
    """
    Prevents multiple messages from being sent in a short time.

    :param message: The message object.
    :return: True if the message can be sent, False otherwise.
    """
    dt = datetime.now()
    last_sent = SENT_TIME.get(message.from_user.id, None)
    if message.media_group_id is None and (last_sent is None or (
            dt - last_sent).total_seconds() >= DELAY_BETWEEN_IMAGES):
        SENT_TIME[message.from_user.id] = dt
        return True
    return False


async def handle_image(message: Message, token: str) -> None:
    """
    Handles image processing based on user requests.

    This function processes an image received as a message and performs various actions based on user requests:
    1. Checks if the user exists and is within usage limits.
    2. Fetches user data and updates the timestamp for the last photo sent.
    3. Downloads the image from Telegram using the provided bot token.
    4. Generates an input file path and logs input image data.
    5. Initiates processing of the image through FastAPI.
    6. Handles various responses from the processing:
       - If the image is successfully downloaded, it is saved, and target image checks are performed.
       - If the processed image paths are received, they are logged and sent as photo messages to the user.
       - Limits on user requests are updated and notifications are sent to the user.
    7. In case of any exceptions or errors during the process, appropriate error messages are sent.
    Note: TODO: split in several functions

    :param message: The message with user data.
    :param token: The Telegram bot token.
    :return: None
    """
    await exist_user_check(message)
    user = await fetch_user_data(message.from_user.id)
    if not (await check_limit(user, message) and await check_time_limit(user, message)):
        return
    await update_photo_timestamp(user.user_id, datetime.now())

    file_path = await message.bot.get_file(message.photo[-1].file_id)
    file_url = f"{TGBOT_PATH}{token}/{file_path.file_path}"
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
                        await message.answer(f'Target image uploaded. Uploads left: {user.targets_left-1}'
                                             f'\nSend your source image')
                        await decrement_targets_left(user.user_id)  # due to async it does not keep up with m.answer

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
                        await message.answer_photo(photo=inp_file, caption=f'Swap faces at @{CONTACTS["botname"]}')
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


async def handle_text(message: Message) -> None:
    """
    Handles text messages from users by providing a response that it cannot handle text message :).

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message)
    await log_text_data(message)
    response_text = (
        "I'm currently set up to process photos only. "
        "Please send me a photo of a person, and I will return their face.")
    await fetch_user_data(message.from_user.id)
    await message.answer(response_text)


async def handle_unsupported_content(message: Message) -> None:
    """
    Handles all other unsupported content by providing a response to the user.

    :param message: The message with user data.
    :return: None
    """
    await message.answer("Sorry, I can't handle this type of content.\n"
                         "Please send me a photo from your gallery, and I will return the face of a person on it.")


async def output_all_users_to_console(message) -> None:
    """
    Outputs all user data to the console. Cleans your own outputs since it's usually too long

    :param message: Dummy args since Message will be sent by the message handler aiogram
    :return: None
    """
    await clear_output_images_by_user_id(message.from_user.id)
    await fetch_all_users_data()


async def set_user_to_premium(message: Message) -> None:
    """
    Sets a user to premium status and provides a response.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message)
    await buy_premium(message.from_user.id)
    user = await fetch_user_data(message.from_user.id)
    await message.answer(f'Congratulations! You got premium status!'
                         f'\nYou have {user.requests_left} attempts left and {user.targets_left} custom target uploads')


async def reset_images_left(message: Message) -> None:
    """
    Resets the number of image processing attempts left for a user and provides a response.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message)
    n = 10
    await set_requests_left(message.from_user.id, n)
    new_number = await fetch_user_data(message.from_user.id)
    await message.answer(f'You have {new_number.requests_left} attempts left')


async def check_status(message: Message) -> None:
    """
    Checks and reports the user's account status and remaining attempts/target uploads.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message)
    user = await fetch_user_data(message.from_user.id)
    is_prem = 'left' if user.status == 'free' else f'with {user.targets_left} target uploads left'
    await message.answer(f'Your have a {user.status} account\nToday you have {user.requests_left} attempts {is_prem}')


async def target_image_check(user: Any, input_image: str) -> Optional[str]:
    """
    Checks if the user is eligible to send a target image and updates user mode accordingly.

    :param user: The user db object.
    :param input_image: The input image path.
    :return: The input image path if conditions are met, None otherwise.
    """
    if user.status == 'premium' and user.receive_target_flag and user.targets_left:
        await update_user_mode(user.user_id, input_image)
        await toggle_receive_target_flag(user.user_id)
        return input_image


async def set_receive_flag(message: Message) -> None:
    """
    Sets the user to be able to send a new target image if they meet the criteria.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message)
    user = await fetch_user_by_id(message.from_user.id)
    if user.status == 'premium' and user.targets_left > 0:
        await toggle_receive_target_flag(message.from_user.id, 1)
        await message.answer('Changing set to receiving a new target.\nSend target image.')
        return
    await message.answer('You need to be a premium user with unspent uploads limit for that. Use /buy_premium function')


async def handle_category_command(message: Message) -> None:
    """
    Handles a command to choose a target category and displays the category buttons.

    :param message: The message with user data.
    :return: None
    """
    keyboard = await create_category_buttons()
    await message.answer("Choose your target category:", reply_markup=keyboard)


async def create_category_buttons() -> InlineKeyboardMarkup:
    """
    Creates inline keyboard buttons for target categories and put them in rows of 2 elements each.
    Dynamically changes buttons.

    :return: InlineKeyboardMarkup containing the category buttons.
    """
    row, keyboard_buttons = [], []
    for category in TARGETS['categories']:
        text = category.capitalize()
        data = f'c_{category}'
        row.append(InlineKeyboardButton(text=text, callback_data=data))
        if len(row) == 2:
            keyboard_buttons.append(row)
            row = []
    if row:
        keyboard_buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


async def show_category_collage(query: CallbackQuery, category: str) -> None:
    """
    Shows a collage of images for a specific category.

    :param query: The callback query.
    :param category: The category for which to show the collage.
    :return: None
    """
    await query.message.answer_photo(photo=PRELOADED_COLLAGES[category])


async def show_images_for_category(query: CallbackQuery, category: str) -> None:
    """
    Shows images for a specific category and provides selection options as well as back button.

    :param query: The callback query.
    :param category: The category for which to show images.
    :return: None
    """
    await show_category_collage(query, category)
    buttons = [[InlineKeyboardButton(text=item["name"], callback_data=item['mode']) for item in chunk]
               for chunk in chunk_list(TARGETS['categories'].get(category, []), 2)]
    back_button = InlineKeyboardButton(text="Back", callback_data="back")
    buttons.append([back_button])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await query.message.edit_text(f"Choose an image from {category.title()}:", reply_markup=keyboard)


def chunk_list(data: list, size: int):
    """
    Splits a list into chunks of a specified size.

    :param data: The list to split into chunks.
    :param size: The size of each chunk.
    :return: A generator yielding chunks of the list.
    """
    for i in range(0, len(data), size):
        yield data[i:i + size]


async def process_image_selection(query: CallbackQuery) -> None:
    """
    Processes the selection of a custom target image and updates user settings.

    :param query: The callback query.
    :return: None
    """
    user_id = query.from_user.id
    data = query.data
    await toggle_receive_target_flag(user_id)
    await update_user_mode(user_id, data)
    await query.message.answer("Target image selected\nSend me a photo, and I'll process it!")
    await fetch_user_data(user_id)
    await query.answer()


def setup_handlers(dp: Any, bot_token: str) -> None:
    """
    Sets up handlers for different commands, messages, and callbacks.

    :param dp: The bot dispatcher object.
    :param bot_token: The Telegram bot token.
    :return: None
    """
    dp.message(Command('start'))(handle_start)
    dp.message(Command('help'))(handle_help)
    dp.message(Command('contacts'))(handle_contacts)
    dp.message(Command('support'))(handle_support)
    dp.message(Command('show_users'))(output_all_users_to_console)
    dp.message(Command('custom_target'))(set_receive_flag)
    dp.message(Command('buy_premium'))(set_user_to_premium)
    dp.message(Command('reset_user'))(reset_images_left)
    dp.message(Command('status'))(check_status)
    dp.message(Command('donate'))(donate_link)
    dp.message(Command('select'))(handle_category_command)
    dp.callback_query()(button_callback_handler)

    async def image_handler(message: Message) -> None:
        if await prevent_multisending(message):
            await handle_image(message, bot_token)
            return
        await message.answer("Please send one photo at a time.")

    dp.message(F.photo)(image_handler)
    dp.message(F.text)(handle_text)
    dp.message(F.sticker | F.video | F.document | F.location | F.poll | F.audio | F.voice | F.contact | F.video_note)(
               handle_unsupported_content)


async def button_callback_handler(query: CallbackQuery) -> None:
    """
    Handles button callbacks from inline keyboards. Categories, modes (numbers) and back button.

    :param query: CallbackQuery.
    :return: None
    """
    if query.data.startswith('c_'):  # Check if the callback data starts with 'c_'
        category = query.data.split('_')[1]
        await show_images_for_category(query, category)
    elif query.data == 'back':
        keyboard = await create_category_buttons()
        await query.message.edit_text("Choose your target category:", reply_markup=keyboard)
    else:
        await process_image_selection(query)
    await query.answer()
