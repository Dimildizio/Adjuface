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


async def premium_confirm(message: Message) -> None:
    markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=LOCALIZATION['get_premium_button'],
                                                                         callback_data="pay")]])
    await message.answer(LOCALIZATION['pay'], reply_markup=markup)
