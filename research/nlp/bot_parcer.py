import asyncio
import cv2
import json
import numpy as np
import yaml

from collections import deque, defaultdict
from PIL import Image
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, FSInputFile


class PhotoForm(StatesGroup):
    waiting_for_image = State()


with open('chats/old_token.yaml', 'r') as f:
    CONFIG = yaml.safe_load(f)

TOKEN = CONFIG['token']
router = Router()
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.include_router(router)
chat_messages = {}
get_chats = lambda chat_id: f"chats/chat_{chat_id}_messages.json"


@dp.message(Command('start'))
async def handle_start(message):
    await message.answer("Don't worry, Tovarishch. Imma justa simple bot, I'll just sit here and listen")


@dp.message(Command('help'))
async def handle_help(message):
    # Provide help information
    help_message = (
        "This bot can only process photos. Here are the available commands:\n"
        "/start - Start the bot\n"
        "/help - Display this help message\n"
        "/face - Get ebal`nik\n"
        "/adjusum - You're too curious\n"

    )
    await message.answer(help_message)


@router.message(Command('face'))
async def handle_face_command(message: Message, state: FSMContext):
    # Set the FSM state to 'waiting_for_image'
    await state.set_state(PhotoForm.waiting_for_image)

    # Now check if the state is set correctly (for demonstration purposes)
    current_state = await state.get_state()
    if current_state == PhotoForm.waiting_for_image.state:
        text = 'State set successfully. Please send the image you want to adjust.'
    else:
        text = 'Failed to set state.'
    print(text)
    await message.answer('Upload your picture')


@router.message(PhotoForm.waiting_for_image, F.photo)
async def process_image(message: Message, state: FSMContext):
    print('received photo')

    # Process the image here
    photo = message.photo[-1]
    file_path = await bot.get_file(photo.file_id)
    # download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path.file_path}"
    abpath = CONFIG['abpath']
    temp_file_path = f"{abpath}/tmp/{photo.file_id}.jpg"
    new_file_path = f"{abpath}/tmp/processed_{photo.file_id}.jpg"

    await bot.download_file(file_path.file_path, destination=temp_file_path)
    image = await get_image(temp_file_path, new_file_path)
    if not image:
        # await message.reply("Couldn't process the image properly.")
        await state.clear()
        return

    await message.answer_photo(FSInputFile(new_file_path), caption="Here is your processed image.")
    await state.clear()


async def get_image(temp_file, new_file):
    image = Image.open(temp_file)
    img_cv = np.array(image)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))
    print(type(faces))
    if type(faces) == np.ndarray:
        for (x, y, w, h) in faces:
            cv2.rectangle(img_cv, (x, y), (x + w, y + h), (0, 255, 0), 2)
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(img_cv, 'ebalnik', (x, y - 10), font, 0.9, (0, 255, 0), 2, cv2.LINE_AA)
        image = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
        image.save(new_file)
        return image


@router.message(Command('adjuface_bot'))
async def handle_adjuface_command(message: Message):
    await message.reply('Move along, Tovarishch. Talk to my ro-bro: @Adjuface_bot')


@router.message(Command('adjusum'))
async def handle_adjustsum_command(message: Message, state: FSMContext):

    summary = await summarize_chat(message.chat.id)
    if summary:
        await message.answer(summary)
    await message.reply('Nothing worth of your interest is going on here')
    await state.clear()


def save_messages_to_file(chat_id: int, messages):
    file_path = get_chats(chat_id)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(list(messages), file, ensure_ascii=False, indent=4)


@router.message()
async def store_message(message: Message):
    chat_id = message.chat.id
    file_path = get_chats(chat_id)

    # Use match case to handle different message types
    match message:
        case Message(text=text):
            content = text
        case Message(photo=_):
            content = "<PHOTO>"
        case Message(video=_):
            content = "<VIDEO>"
        case Message(document=_):
            content = "<DOCUMENT>"
        case Message(sticker=_):
            content = "<STICKER>"
        case _:
            content = "<UNKNOWN TYPE>"

    user = message.from_user
    # Prepare the message data
    message_data = {
        "user_id": user.id,
        "username": user.username or user.last_name or user.first_name or "anonymous_user",
        # Handle case where username might be None
        "text": content}

    # Load existing messages if the file exists, else start with an empty deque
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            existing_messages = deque(json.load(file), maxlen=1000)
    except FileNotFoundError:
        existing_messages = deque(maxlen=1000)

    existing_messages.append(message_data)
    save_messages_to_file(chat_id, existing_messages)


@router.message(Command('sum'))
async def handle_summarize_command(message: Message):
    await message.reply('wait for it')
    # summary = await summarize_chat(message.chat.id)
    # await message.answer(summary)


async def summarize_chat(chat_id):
    return
    # await user_based_summarization(chat_id)
    # await general_summarization(chat_id)


async def summarize_text(text, summarizer):
    """
    Summarizes a given text using a pre-defined summarization model.
    """
    try:
        summary = summarizer(text, max_length=130, min_length=25, truncation=True)
        summary_text = summary[0]['summary_text'] if summary else 'Summary unavailable'
    except Exception as e:
        print(f"Error during summarization: {e}")
        summary_text = 'Summary unavailable'

    return summary_text


async def user_based_summarization(chat_id):
    file_path = get_chats(chat_id)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            messages = json.load(file)
    except FileNotFoundError:
        return "No messages to summarize."

    # Group messages by user
    user_messages = defaultdict(list)
    for msg in messages:
        if msg['text'] and isinstance(msg['text'], str):
            user_messages[msg['user_id']].append(msg['text'])

    # Generate summary for each user
    # user_summaries = []
    for user_id, texts in user_messages.items():
        text_to_summarize = " ".join(texts)
        # summary = await summarize_text(text_to_summarize)
        # user_summaries.append((user_id, summary))
        print(text_to_summarize)
    # Print or return the summaries
    # for user_id, summary in user_summaries:
    #    print(f"User {user_id} said: {summary}")

    # return user_summaries  # or process as needed


async def general_summarization(chat_id):
    file_path = get_chats(chat_id)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            messages = json.load(file)
    except FileNotFoundError:
        return "No messages to summarize."

    # Prepare messages, keeping order and prefixing with user info
    prepared_messages = [f"User {msg['user_id']} said: {msg['text']}"
                         for msg in messages if msg['text'] and isinstance(msg['text'], str)]

    # Combine into a single text for summarization
    text_to_summarize = " ".join(prepared_messages)

    # Generate general summary of the entire conversation
    # general_summary = await summarize_text(text_to_summarize)

    # Print or return the general summary
    print(text_to_summarize)
    # return general_summary


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
