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

Example:
    Deploy the bot and interact with it through Telegram. Use commands like /start, /help, and /donate ;) to navigate
    the bot's features. Send a photo to the bot, and it will process it according to the selected target face or
    category.
"""


from aiogram import F
from aiogram.filters.command import Command
from aiogram.types import Message
from typing import Any
from bot.handlers.commands import handle_start, handle_help, handle_contacts, handle_support, handle_unsupported_content, \
                                  output_all_users_to_console, set_receive_flag, check_status, handle_text, \
                                  reset_images_left, donate_link, handle_category_command, button_callback_handler, \
                                  handle_image
from bot.handlers.callbacks import premium_confirm
from bot.handlers.checks import prevent_multisending, utility_func
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
    dp.message(Command('show_users'))(output_all_users_to_console)
    dp.message(Command('util'))(utility_func)
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
