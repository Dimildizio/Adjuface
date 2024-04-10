"""
This module contains the implementation of command handlers for a Telegram bot designed for face swapping
and other image manipulation tasks. Utilizing the Aiogram library, it defines functions that respond to specific
commands issued by users, enabling interactions such as starting the bot, requesting help, managing user account
settings, and initiating image processing requests.

Key Features:
- Command Handling: Implements functions to respond to Telegram commands like /start, /help, /donate, etc.
- User Interaction: Facilitates direct interactions with users through informative messages and prompts for input,
  enhancing the bots usability and engagement.
- Premium Features Management: Provides mechanisms for users to access and manage premium features,
  including custom target uploads and extended processing capabilities.
- Image Processing Initiation: Triggers the face swapping process based on user commands, supporting both
  automated target selection and user-defined targets for premium accounts.

Usage:
- Handlers defined in this module should be registered with an Aiogram Dispatcher in the bots main.py setup file,
  allowing them to respond to user commands.
- This module works in conjunction with other parts of the bot`s architecture, such as utilities for image processing,
  user data management, and asynchronous task handling, to provide a cohesive user experience.

Dependencies:
- Aiogram: For defining and managing Telegram bot command handlers.
- Bot-specific utilities and services: For tasks like image processing, user data management, and interaction logging.

Configuration:
- Before deployment, ensure that all necessary configurations, such as db, command keywords and premium feature
  settings, are correctly defined and integrated with the bots overall functionality.

Example:
- A user sends the /start command to the bot. This module processes the command and responds with a welcome message
  and instructions for using the bots features.
"""

from aiogram.types import Message, CallbackQuery, FSInputFile, ReplyKeyboardRemove
from datetime import datetime
from yoomoney import Client, Quickpay

from bot.database.db_users import exist_user_check, toggle_receive_target_flag, buy_premium, insert_payment, \
                                  set_requests_left, delete_all_payments_for_user
from bot.database.db_fetching import fetch_user_by_id, fetch_user_data, fetch_all_users_data, operation_not_in_payments
from bot.database.db_logging import log_error, log_text_data
from bot.database.db_images import clear_output_images_by_user_id
from bot.handlers.callbacks import create_category_buttons, show_images_for_category, process_image_selection, \
                                   create_location_request_keyboard, confirm_pay
from bot.handlers.checks import image_handler_checks, is_premium
from bot.handlers.voices import synthesize_speech
from bot.handlers.constants import CONTACTS, LOCALIZATION, PRELOADED_COLLAGES, LANGUAGE, PRICE, DELAY_BETWEEN_IMAGES, \
                                   CURRENCY_URL, CURRENCY_API, WEATHER_URL, WEATHER_API, YOUTOK, YOUNUM, FREE_REQUESTS
from bot.handlers.image_utils import handle_image_constants, image_handler_logic, send_image
from bot.handlers.drawer import request_sd
from utils import get_exchange_rate, get_weather


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


async def handle_location(message: Message) -> None:
    """
    Handles the message containing the user's location.
    """
    if not await is_premium(message):
        return await handle_unsupported_content(message)
    await message.answer(LOCALIZATION['weather_word'], reply_markup=ReplyKeyboardRemove())
    try:
        await message.delete()
    except RuntimeError as e:
        print(f"Error deleting message: {e}")
        await log_error(message.from_user.id, error_message=str(e))
    url = WEATHER_URL.format(latitude=message.location.latitude, longitude=message.location.longitude,
                             lang=LANGUAGE, api_key=WEATHER_API)
    weather = await get_weather(url, LOCALIZATION['weather_format'])
    await message.answer(weather)


async def handle_hello(message: Message) -> None:
    """
    Sends currency rates and weather
    :param message: aiogram types.Message class
    :return: 
    """
    if not await is_premium(message):
        return await handle_unsupported_content(message)
    result = LOCALIZATION['morning']
    for cur1, cur2 in (('btc', 'usd'), ('usd', 'rub'), ('cny', 'rub')):
        cur = await get_exchange_rate(cur1, cur2, f'{CURRENCY_URL}{cur1}.json')
        try:
            if 'Error' in cur:  # assert 'Error' not in cur
                print('Error fetching from basic url')
                raise RuntimeError('Error fetching currency from basic url')
        except RuntimeError as e:
            await log_error(message.from_user.id, error_message=str(e), details=f'{cur1}-{cur2} at {datetime.now()}')
            cur = await get_exchange_rate(cur1, cur2, f'{CURRENCY_API}{cur1}.json')
        result = result + cur

    keyboard = await create_location_request_keyboard()
    await message.answer(result+LOCALIZATION['weather_keyboard'], reply_markup=keyboard)


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


async def handle_text(message: Message) -> None:
    """
    Handles text messages from users by providing a response that it cannot handle text message :).

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message.from_user)
    await log_text_data(message)
    await fetch_user_data(message.from_user.id)
    if await is_premium(message):
        return await handle_text_synt(message)
    await message.answer(LOCALIZATION['wrong_input'])


async def handle_unsupported_content(message: Message) -> None:
    """
    Handles all other unsupported content by providing a response to the user.

    :param message: The message with user data.
    :return: None
    """

    await message.answer(LOCALIZATION['wrong_input'])


async def reset_images_left(message: Message) -> None:
    """
    Resets the number of image processing attempts left for a user and provides a response.

    :param message: The message with user data.
    :return: None
    """
    await exist_user_check(message.from_user)
    await set_requests_left(message.from_user.id, FREE_REQUESTS)
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
    text = LOCALIZATION['status'].format(status=user.status, exp=expiration, req=user.requests_left)
    if user.status == 'premium':
        text = text + LOCALIZATION['status_prem'].format(is_prem=user.targets_left)
    await message.answer(text)


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


async def output_all_users_to_console(message: Message) -> None:
    """
    Outputs all user data to the console. Cleans your own outputs since it's usually too long

    :param message: Dummy args since Message will be sent by the message handler aiogram
    :return: None
    """
    await clear_output_images_by_user_id(message.from_user.id)
    await fetch_all_users_data()


async def handle_category_command(message: Message) -> None:
    """
    Handles a command to choose a target category and displays the category buttons.

    :param message: The message with user data.
    :return: None
    """
    keyboard = await create_category_buttons()
    await message.answer(LOCALIZATION['category'], reply_markup=keyboard)


async def handle_text_synt(message: Message) -> None:
    """
    Handles a message containing text by synthesizing speech and sending it as an audio reply.

    :param message: The message containing the text to be synthesized.
    :return: None
    """
    address = await synthesize_speech(message.text)
    await message.answer_audio(FSInputFile(address))


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


async def handle_draw(message: Message):
    """
    Handles the draw command by parsing the input text and triggering the drawing logic.
    """
    command, *args = message.text.split(maxsplit=1)
    text_to_draw = args[0] if args else None
    if text_to_draw is None:
        return await message.answer("No text provided")
    await message.answer(f"Prompt: {text_to_draw}")
    filename = await request_sd(text_to_draw)
    if filename:
        return await send_image(message, filename)
    return await message.answer("Error has occurred while drawing")

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


async def check_premium_payment(query):
    youser = Client(YOUTOK)
    history = youser.operation_history()
    uid = query.from_user.id
    await exist_user_check(query.from_user)
    for op in history.operations:
        # splot op.label on user id and unique quick pay id
        # figure out how to take only past day operations (maybe from date) without filtering them
        if op.label == str(uid) and op.status == 'success' and op.amount >= PRICE*0.9 \
         and await operation_not_in_payments(uid, op.operation_id):
            # and op.operation_id not in db
            await insert_payment(uid, op.operation_id, op.datetime)
            await set_user_to_premium(query)
            return  # Write user: op.operation_id to db
        else:
            print(f'{op.label} of {uid} not in')
    await query.answer(LOCALIZATION['no_payment'], show_alert=True)


async def generate_payment(query):
    """later add unique payment id to write in db to enable / disable it and prevent adding premium each click
        after 1 purchase, add quick pay unique id to db as well as operation_id """
    # generate db_pay_id here

    paylink = Quickpay(receiver=YOUNUM, quickpay_form="button", targets="Startup", paymentType="SB", sum=PRICE,
                       label=query.from_user.id)  # add db_pay_id with a split symbol here
    markup = await confirm_pay()
    await query.message.answer(LOCALIZATION['ask_confirm_pay'])
    await query.message.answer(paylink.redirected_url, reply_markup=markup)


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
            await generate_payment(query)  # set_user_to_premium(query)  # answer(LOCALIZATION['got_premium'])
        case 'check_payment':
            await check_premium_payment(query)
        case _:
            await process_image_selection(query)
    await query.answer()
