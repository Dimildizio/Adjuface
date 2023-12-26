from aiogram import F
from aiogram.filters.command import Command
# from bot.user_logger import log_user
# from segmentation.get_image import process_image


async def handle_start(message):
    await message.answer("Welcome! Send me a photo, and I'll process it.")


async def handle_help(message):
    help_message = (
        "This bot can only process photos. Here are the available commands:\n"
        "/start - Start the bot\n"
        "/help - Display this help message\n"
        "Send me a photo, and I'll process it!"
    )
    await message.answer(help_message)


async def handle_image(message, bot):
    pass
    # Image processing logic here (simplified for brevity)


def setup_handlers(dp):
    dp.message(Command('start'))(handle_start)
    dp.message(Command('help'))(handle_help)
    dp.message(F.photo)(handle_image)
