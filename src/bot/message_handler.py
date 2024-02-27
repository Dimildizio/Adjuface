"""
This module serves as the central hub for dispatching incoming Telegram messages to their respective handlers.
It leverages the Aiogram library to efficiently manage and route user messages, including commands, text inputs,
and multimedia content, to the appropriate functionalities within the bot's architecture.

Purpose:
- To act as the primary interface between the Telegram API and the bot's internal logic.
- To classify and route messages based on their content type (e.g., commands, photos, text) and context.

Key Responsibilities:
- Registering command handlers and callback query handlers from the `commands.py` module.
- Initiating the bot's response to non-command messages, such as direct text inputs or photo submissions,
  by invoking the relevant processing functions.
- Implementing filters and checks to manage the flow of incoming messages and ensure they are handled appropriately,
  including rate limiting and content validation.

Usage:
- This module is intended to be used as part of the bot's startup process, which is in main.py with handlers for
different types of Telegram messages and actions.
- Handlers defined in `commands.py` and other modules are imported and registered with the `Dispatcher` here.

Example:
- Upon receiving a message, this module determines the appropriate action, such as processing an image submitted by the
user, and routes the message to the corresponding function for handling.

Note:
- This module focuses on message dispatching and routing. Specific command implementations and business logic are
  contained in `commands.py` and other dedicated modules, keeping the bot's architecture modular and maintainable.
"""


from aiogram import F
from aiogram.filters.command import Command
from aiogram.types import Message
from typing import Any

from bot.handlers.callbacks import premium_confirm
from bot.handlers.checks import prevent_multisending, utility_func
from bot.handlers.voices import handle_voice
from bot.handlers.commands import handle_start, handle_help, handle_contacts, handle_support, handle_image, \
                                  output_all_users_to_console, set_receive_flag, check_status, handle_text, \
                                  reset_images_left, donate_link, handle_category_command, button_callback_handler, \
                                  handle_unsupported_content, handle_hello, handle_location
from bot.handlers.constants import LOCALIZATION


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
    dp.message(Command('hello'))(handle_hello)
    dp.message(Command('show_users'))(output_all_users_to_console)
    dp.message(Command('util'))(utility_func)
    dp.message(Command('target'))(set_receive_flag)
    dp.message(Command('buy_premium'))(premium_confirm)
    dp.message(Command('reset_user'))(reset_images_left)
    dp.message(Command('status'))(check_status)
    dp.message(Command('donate'))(donate_link)
    dp.message(Command('menu'))(handle_category_command)
    dp.callback_query()(button_callback_handler)

    async def generic_handler(func, message: Message) -> None:
        if await prevent_multisending(message):
            await func(message, bot_token)
            return
        await message.answer(LOCALIZATION['too_fast'])

    async def voice_handler(message: Message) -> None:
        await generic_handler(handle_voice, message)

    async def image_handler(message: Message) -> None:
        await generic_handler(handle_image, message)

    dp.message(F.photo)(image_handler)
    dp.message(F.text)(handle_text)
    dp.message(F.voice)(voice_handler)
    dp.message(F.location)(handle_location)
    dp.message(F.sticker | F.audio | F.video | F.document | F.poll | F.contact | F.video_note)(
               handle_unsupported_content)
