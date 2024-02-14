from aiogram.types import Message, CallbackQuery
from bot.handlers.checks import image_handler_checks
from bot.handlers.constants import CONTACTS, LOCALIZATION, PRELOADED_COLLAGES
from bot.handlers.callbacks import create_category_buttons, show_images_for_category, process_image_selection
from bot.handlers.image_utils import handle_image_constants, image_handler_logic
from bot.db_requests import exist_user_check, fetch_user_by_id, log_text_data, fetch_user_data, set_requests_left, \
                            toggle_receive_target_flag, clear_output_images_by_user_id, fetch_all_users_data, \
                            log_error, buy_premium

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
