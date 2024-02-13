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
  - TODO: log time and delete from user filenames history adresses deleted files

Example:
    Deploy the bot and interact with it through Telegram. Use commands like /start, /help, and /donate ;) to navigate
    the bot's features. Send a photo to the bot, and it will process it according to the selected target face or
    category.
"""


import aiohttp
import json

from datetime import datetime, timedelta
from aiogram import F
from aiogram.filters.command import Command
from aiogram.types import FSInputFile, Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot.db_requests import set_requests_left, update_user_mode, log_input_image_data, exist_user_check, \
                            log_output_image_data, log_text_data, fetch_user_data, fetch_all_users_data, \
                            decrement_requests_left, buy_premium, update_photo_timestamp, fetch_user_by_id, \
                            toggle_receive_target_flag, decrement_targets_left, clear_output_images_by_user_id, \
                            fetch_recent_errors, log_error
from typing import Any, Tuple, List
from utils import get_yaml, get_localization, load_target_names, generate_filename, chunk_list, save_img


# Define constants
SENT_TIME = {}   # dictionary with user IDs and timestamps
CONFIG = get_yaml('config.yaml')
CONTACTS = get_yaml()
FACE_EXTRACTION_URL = CONFIG['fastapi_swapper']
TGBOT_PATH = CONFIG['bot_path']
DELAY_BETWEEN_IMAGES = CONFIG['img_delay']
LOCALIZATION = get_localization(lang=CONFIG['language'])

TARGETS = load_target_names(CONFIG['language'])
PRELOADED_COLLAGES = {category: FSInputFile(collage_path) for category, collage_path in TARGETS['collages'].items()}
print(TARGETS)


async def handle_start(message: Message) -> None:
    """
    Handles the start command from a user by checking their existence, sending a welcome message,
    and prompting for a photo.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message.from_user)
    limits = await fetch_user_by_id(message.from_user.id)
    welcome = LOCALIZATION['welcome'].format(req=limits.requests_left)
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
    await message.answer(LOCALIZATION['support_request'])


async def handle_contacts(message) -> None:
    """
    Sends the contact information to user.

    :param message: The user data message.
    :return: None
    """
    #                                          f"\nGithub: {CONTACTS['github']}\n")
    await message.answer(LOCALIZATION['contact_me'].format(tg=CONTACTS['telegram']))


async def donate_link(message) -> None:
    """
    Sends a message to the user with information on how to support via cryptocurrency.

    :param message: User data message.
    :return: None
    """
    await message.answer(LOCALIZATION['donate'])
    await message.answer(CONTACTS['cryptohash'])


async def handle_help(message: Message) -> None:
    """
    Sends a help message to the user with available commands.

    :param message: The user data message from the user.
    :return: None
    """
    await message.answer(LOCALIZATION['help_message'])


async def check_limit(user: Any, message: Message) -> bool:
    """
    Checks if the user has reached their request limit.

    :param user: The user class object.
    :param message: The user data message from the user.
    :return: True if the user has requests left, False otherwise.
    """
    if user.requests_left <= 0:
        await message.answer(LOCALIZATION['no_attempts'])
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
        await message.answer(LOCALIZATION['too_fast'])
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


async def image_handler_checks(message: Message) -> Any:
    """
    Checks the user status and limits.

    :param message: The message with user data.
    :return: User data if checks pass, else None.
    """
    await exist_user_check(message.from_user)
    user = await fetch_user_data(message.from_user.id)
    if not (await check_limit(user, message) and await check_time_limit(user, message)):
        return None
    await update_photo_timestamp(user.user_id, datetime.now())
    return user


async def handle_image_constants(message: Message, token: str, user: Any) -> Tuple[str, str]:
    """
    Handles constants related to image processing.

    :param message: The message with user data.
    :param token: The Telegram bot token.
    :param user: User data.
    :return: File URL and input path.
    """
    file_path = await message.bot.get_file(message.photo[-1].file_id)
    file_url = f"{TGBOT_PATH}{token}/{file_path.file_path}"
    input_path = await generate_filename('target_images' if user.receive_target_flag else 'original')
    await log_input_image_data(message, input_path)
    return file_url, input_path


async def handler_image_send(message: Message, output_paths: List) -> bool:
    """
    Handles sending processed images.

    :param message: The message with user data.
    :param output_paths: List of output image paths.
    :return: True if successful, else False.
    """
    for output_path in output_paths:
        user = await fetch_user_data(message.from_user.id)
        if not (await check_limit(user, message)):
            return False
        inp_file = FSInputFile(output_path)
        await message.answer_photo(photo=inp_file,
                                   caption=LOCALIZATION['captions'].format(botname=CONTACTS['botname']))
        print('Image sent')
    return True


async def image_handler_received_result(message: Message, user: Any, response: aiohttp.ClientResponse,
                                        input_path: str) -> bool:
    """
    Handles the result of image processing when received successfully.

    :param message: The message with user data.
    :param user: User data.
    :param response: The response from the processing request.
    :param input_path: The input image path.
    :return: True if successful, False otherwise.
    """
    image_paths = json.loads(await response.text())
    await log_output_image_data(message, input_path, image_paths)  # logging to db
    if not await handler_image_send(message, image_paths):
        return False
    await decrement_requests_left(user.user_id, n=len(image_paths))
    await message.answer(LOCALIZATION['attempts_left'].format(
                         limit=max(0, user.requests_left - len(image_paths))))
    return True


async def image_handler_result_failed(message: Message, response: aiohttp.ClientResponse) -> None:
    """
    Handles the case when the result of image processing failed.

    :param message: The message with user data.
    :param response: The response from the processing request.
    :return: None
    """
    error_message = await response.text()
    print(error_message)
    await message.answer(LOCALIZATION)


async def image_handler_swapper(message: Message, user: Any, session: aiohttp.ClientSession, input_path: str) -> bool:
    """
    Handles FASTAPI interaction for swapping of faces.

    :param message: The message with user data.
    :param user: User data.
    :param session: The aiohttp client session.
    :param input_path: The input image path.
    :return: True if successful, False otherwise.
    """
    async with session.post(FACE_EXTRACTION_URL,
                            data={'file_path': input_path, 'mode': user.mode}
                            ) as response:

        print('Sending image path through fastapi')
        if response.status == 200:
            if not await image_handler_received_result(message, user, response, input_path):
                return False
        else:
            await image_handler_result_failed(message, response)
        return True


async def image_handler_load(message: Message, user: Any, response: aiohttp.ClientResponse, input_path: str) -> bool:
    """
    Handles downloading of images.

    :param message: The message with user data.
    :param user: User data.
    :param response: The response from the download request.
    :param input_path: The input image path.
    :return: True if successful, False otherwise.
    """
    content = await response.read()
    await message.answer(LOCALIZATION['img_received'])
    await save_img(content, input_path)
    print('Image downloaded')
    return await target_image_check(message, user, input_path)


async def image_handler_download_failed(message: Message, response: aiohttp.ClientResponse) -> None:
    """
    Handles the case when image download failed.

    :param message: The message with user data.
    :param response: The response from the download request.
    :return: None
    """
    error_message = await response.text()
    print(error_message)
    await message.answer(LOCALIZATION['failed'])


async def image_handler_logic(message, user, file_url, input_path):
    """
    Handles all image interaction logic

    1. Downloads the image from Telegram using the provided bot token.
    2. Generates an input file path and logs input image data.
    3. Initiates processing of the image through FastAPI.
    4. Handles various responses from the processing:
       - If the image is successfully downloaded, it is saved, and target image checks are performed.
       - If the processed image paths are received, they are logged and sent as photo messages to the user.
       - Limits on user requests are updated and notifications are sent to the user.
    5. In case of any exceptions or errors during the process, appropriate error messages are sent.

    :param message: The message with user data.
    :param user: User data.
    :param file_url: The url to download a file from tg.
    :param input_path: The input image path.
    :return: None
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as response:
            if response.status == 200:
                if await image_handler_load(message, user, response, input_path):
                    return
            else:
                await image_handler_download_failed(message, response)
                return
        await image_handler_swapper(message, user, session, input_path)


async def handle_image(message: Message, token: str) -> None:
    """
    Handles image processing based on user requests.

    This function processes an image received as a message and performs various actions based on user requests:
    1. Checks if the user exists and is within usage limits.
    2. Fetches user data and updates the timestamp for the last photo sent.
    3. If any error occurs - sends user a message.

    :param message: The message with user data.
    :param token: The Telegram bot token.
    :return: None
    """

    user = await image_handler_checks(message)
    if not user:
        return
    file_url, input_path = await handle_image_constants(message, token, user)
    try:
        await image_handler_logic(message, user, file_url, input_path)
    except Exception as e:
        print(e)
        await log_error(user.user_id, error_message=str(e), details=input_path)
        await message.answer(LOCALIZATION['failed'])


async def handle_text(message: Message) -> None:
    """
    Handles text messages from users by providing a response that it cannot handle text message :).

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message.from_user)
    await log_text_data(message)
    await fetch_user_data(message.from_user.id)
    await message.answer(LOCALIZATION['wrong_input'])


async def handle_unsupported_content(message: Message) -> None:
    """
    Handles all other unsupported content by providing a response to the user.

    :param message: The message with user data.
    :return: None
    """
    await message.answer(LOCALIZATION['wrong_input'])


async def set_user_to_premium(query: CallbackQuery) -> None:
    """
    Sets a user to premium status and provides a response.

    :param query: The button callback with user data.
    :return: None
    """
    await exist_user_check(query.from_user)
    await buy_premium(query.from_user.id)
    user = await fetch_user_data(query.from_user.id)
    await query.message.answer(LOCALIZATION['got_premium'].format(req=user.requests_left,
                                                                  targets=user.targets_left,
                                                                  exp=user.premium_expiration))
    await donate_link(query.message)


async def premium_confirm(message):
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=LOCALIZATION['get_premium_button'],
                                                                         callback_data="pay")]])
    await message.answer(LOCALIZATION['pay'], reply_markup=markup)


async def reset_images_left(message: Message) -> None:
    """
    Resets the number of image processing attempts left for a user and provides a response.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message.from_user)
    n = 10
    await set_requests_left(message.from_user.id, n)
    new_number = await fetch_user_data(message.from_user.id)
    await message.answer(LOCALIZATION['attempts_left'].format(limit=new_number.requests_left))


async def check_status(message: Message) -> None:
    """
    Checks and reports the user's account status and remaining attempts/target uploads.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message.from_user)
    user = await fetch_user_data(message.from_user.id)
    expiration = user.premium_expiration or ' '
    await message.answer(LOCALIZATION['status'].format(status=user.status,
                                                       exp=expiration,
                                                       req=user.requests_left,
                                                       is_prem=user.targets_left))


async def target_image_check(message: Message, user: Any, input_image: str) -> bool:
    """
    Checks if the user is eligible to send a target image and updates user mode accordingly.

    :param message: The message with user data.
    :param user: The user db object.
    :param input_image: The input image path.
    :return: The input image path if conditions are met, None otherwise.
    """
    if user.status == 'premium' and user.receive_target_flag and user.targets_left:
        await update_user_mode(user.user_id, input_image)
        await toggle_receive_target_flag(user.user_id)
        await message.answer(LOCALIZATION['target_uploaded'].format(left=user.targets_left - 1))
        await decrement_targets_left(user.user_id)  # due to async it does not keep up with m.answer
        return True


async def set_receive_flag(message: Message) -> None:
    """
    Sets the user to be able to send a new target image if they meet the criteria.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message.from_user)
    user = await fetch_user_by_id(message.from_user.id)
    if user.status == 'premium' and user.targets_left > 0:
        await toggle_receive_target_flag(message.from_user.id, 1)
        await message.answer(LOCALIZATION['target_request'])
        return
    await message.answer(LOCALIZATION['not_premium'])


async def handle_category_command(message: Message) -> None:
    """
    Handles a command to choose a target category and displays the category buttons.

    :param message: The message with user data.
    :return: None
    """
    keyboard = await create_category_buttons()
    await message.answer(LOCALIZATION['category'], reply_markup=keyboard)


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
    back_button = InlineKeyboardButton(text=LOCALIZATION['button_back'], callback_data="back")
    buttons.append([back_button])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await query.message.edit_text(f"{LOCALIZATION['subcategory']} {category.title()}:", reply_markup=keyboard)


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
    await query.message.answer(LOCALIZATION['selected'])
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
    dp.message(Command('target'))(set_receive_flag)
    dp.message(Command('buy_premium'))(premium_confirm)
    dp.message(Command('reset_user'))(reset_images_left)
    dp.message(Command('status'))(check_status)
    dp.message(Command('donate'))(donate_link)
    dp.message(Command('menu'))(handle_category_command)
    dp.callback_query()(button_callback_handler)

    async def image_handler(message: Message) -> None:
        if await prevent_multisending(message):
            await handle_image(message, bot_token)
            return
        await message.answer(LOCALIZATION['too_fast'])

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
    match query.data:
        case data if data.startswith('c_'):  # Check if the callback data starts with 'c_'
            category = data.split('_')[1]
            await show_images_for_category(query, category)
        case 'back':
            keyboard = await create_category_buttons()
            await query.message.edit_text(LOCALIZATION['category'], reply_markup=keyboard)
        case 'pay':
            await set_user_to_premium(query)  # answer(LOCALIZATION['got_premium'])
        case _:
            await process_image_selection(query)
    await query.answer()


async def output_all_users_to_console(message) -> None:
    """
    Outputs all user data to the console. Cleans your own outputs since it's usually too long

    :param message: Dummy args since Message will be sent by the message handler aiogram
    :return: None
    """
    await clear_output_images_by_user_id(message.from_user.id)
    await fetch_all_users_data()
    await utility_func(message)


async def utility_func(message: Message) -> None:
    """
    Dev func to do situational stuff to the user.

    :param message: The message with user data.
    :return: None
    """
    await display_recent_errors()
    try:
        print()
        send_path = r''
        await message.answer_photo(FSInputFile(send_path))
    except Exception as e:
        await log_error(message.from_user.id, error_message='UtilityFuncError:'+str(e))
        print('Attention! We got an error!', e)
    await display_recent_errors()


async def display_recent_errors():
    recent_errors = await fetch_recent_errors(limit=5)  # Fetch the last 5 errors
    if recent_errors:
        print("Recent Errors:")
        for error in recent_errors:
            user_info = f"User ID: {error['user_id']}, Username: {error['username']}, Name: {error['first_name']} " \
                        f"{error['last_name']}" if error['user_id'] else "User ID: None"
            print(f"ID: {error['id']}, {user_info}, "
                  f"Message: {error['error_message']}, Details: {error['details']}, "
                  f"Timestamp: {error['timestamp']}")
    else:
        print("No recent errors found.")
