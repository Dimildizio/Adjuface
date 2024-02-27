import aiohttp
import uuid
from aiofiles import open as aio_open
from aiogram.types import Message
from typing import Any

from bot.handlers.checks import is_premium
from bot.handlers.constants import TGBOT_PATH, TTS_AUTH, TTS_TOKEN, TTS_LINK, TGBOT_NAME
from utils import generate_filename


async def handle_voice(message: Message, token):
    if not await is_premium(message):
        return

    input_path = await download_voice_file(message, token)
    if input_path:
        recognized_data = await recognize_speech(input_path)
        await respond_with_recognized_text(message, recognized_data)


async def recognize_speech(input_path: str):
    access_token = await get_api_access()
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'audio/ogg;codecs=opus'}

    async with aiohttp.ClientSession() as session:
        async with aio_open(input_path, 'rb') as audio_file:
            audio_data = await audio_file.read()
            async with session.post(TTS_LINK, headers=headers, data=audio_data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return None


async def download_voice_file(message: Message, token: str):
    file_path = await message.bot.get_file(file_id=message.voice.file_id)
    file_url = f"{TGBOT_PATH}{token}/{file_path.file_path}"
    input_path = await generate_filename('voice', 'audio', 'ogg')

    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as response:
            if response.status == 200:
                with open(input_path, 'wb') as fd:
                    while True:
                        chunk = await response.content.read(1024)  # Read 1024 bytes
                        if not chunk:
                            break
                        fd.write(chunk)
                print(f"File saved to {input_path}")
                return input_path
            else:
                print("Failed to download the file.")
                return None


async def respond_with_recognized_text(message: Message, recognized_data: Any) -> None:
    if recognized_data:
        recognized_text = recognized_data.get("result", ["Could not recognize"])
        result = await sign_text(recognized_text)
        print(f"Recognized text: {result}")
        await message.answer(result)
    else:
        print("Failed to recognize speech.")
        await message.answer("Failed to recognize speech.")


async def sign_text(text: str) -> str:
    text = '\n\n'.join(text)
    return f'Текст вашего сообщения:\n\n{text}\n\nРаспознано с @{TGBOT_NAME}'.replace('. ', '.\n')


async def get_api_access() -> str:
    headers = {
        'Authorization': f'Basic {TTS_TOKEN}',
        'RqUID': str(uuid.uuid4()),
        'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'scope': 'SALUTE_SPEECH_PERS'}

    async with aiohttp.ClientSession() as session:
        async with session.post(TTS_AUTH, headers=headers, data=data, ssl=False) as response:
            if response.status == 200:
                response_json = await response.json()
                return response_json['access_token']
            else:
                raise ValueError(f"Failed to get access token, status code: {response.status}")
