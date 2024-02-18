"""
This module focuses on handling callback queries from inline keyboard interactions within the Telegram bot.
It includes functionalities for dynamically creating category selection buttons, displaying image collages
for selected categories, processing user selections for custom target images, and confirming premium feature
subscriptions.

Key Functionalities:
- Dynamic creation of inline keyboard buttons for navigating through face swapping categories.
- Display of preloaded image collages corresponding to user-selected categories to guide their choices.
- Processing of user selections for custom target images, facilitating personalized face swapping experiences.
- Confirmation of premium subscriptions, enabling users to access enhanced features of the bot.

Usage:
- The functions within this module are intended to be used with main.py and commands.py as callback query handlers.
- They are invoked in response to user interactions with inline keyboards presented by the bot during various stages
  of the face swapping process.

Example:
- When a user selects a category from the bot's menu, `show_category_collage` is called to display a collage of
  target faces from that category. Users can then make further selections or confirm actions, triggering other
  handlers like `process_image_selection` or `premium_confirm`.

Dependencies:
- Aiogram: For creating and managing the Telegram bot's callback queries.
- Application-specific utilities and constants: For accessing preloaded images, localization strings,
  and other bot settings.
"""


from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from bot.db_requests import toggle_receive_target_flag, update_user_mode, fetch_user_data
from bot.handlers.constants import PRELOADED_COLLAGES, TARGETS, LOCALIZATION
from utils import chunk_list


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
    await query.message.answer(f"{LOCALIZATION['subcategory']} {category.title()}:", reply_markup=keyboard)

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


async def premium_confirm(message: Message) -> None:
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=LOCALIZATION['get_premium_button'],
                                                                         callback_data="pay")]])
    await message.answer(LOCALIZATION['pay'], reply_markup=markup)
