import aiohttp
import uuid
import math

from aiogram.types import Message, FSInputFile
from pydub import AudioSegment
from typing import List

from bot.handlers.checks import is_premium
from bot.handlers.constants import TGBOT_PATH, TTS_AUTH, TTS_TOKEN, TTS_LINK, STT_LINK, TGBOT_NAME, TTS_AUDIO_SIZE
from utils import generate_filename


async def handle_voice(message: Message, token):
    if not await is_premium(message):
        return
    input_path = await download_voice_file(message, token)
    if input_path:
        recognized_data = await split_and_recognize(input_path)
        await respond_with_recognized_text(message, recognized_data)


async def split_and_recognize(input_path):
    chunks_paths = await split_file_by_size(input_path, TTS_AUDIO_SIZE)
    recognized_texts = []
    for chunk_path in chunks_paths:
        recognized_data = await recognize_speech(chunk_path)
        if recognized_data:
            recognized_text = recognized_data.get("result", ["----Could not recognize----"])
            recognized_emotion = recognized_data.get("emotions", ["----Could not recognize----"])
            recognized_emotion = [',\n'.join([f"{key}: {round(value, 3)}" for key, value in recognized_emotion[0].items()])]
            recognized_texts.extend(recognized_text)
            recognized_texts.extend(recognized_emotion)
            # Clean up chunk file after processing
            #os.remove(chunk_path)
            print(f'{chunk_path} recognized')
        else:
            print(f'we got problem {chunk_path}')
    print('RESULT:', recognized_texts)
    return recognized_texts


async def recognize_speech(input_path: str):
    print('\n\nstart recognition\n\n')
    access_token = await get_api_access()
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'audio/ogg;codecs=opus'}

    async with aiohttp.ClientSession() as session:
        async with aio_open(input_path, 'rb') as audio_file:
            audio_data = await audio_file.read()
            async with session.post(STT_LINK, headers=headers, data=audio_data) as response:
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


async def respond_with_recognized_text(message: Message, recognized_texts: list) -> None:
    if recognized_texts:
        # Since recognized_texts is already a list of strings, we can directly join them.
        result_text = recognized_texts#'\n\n'.join(recognized_texts)
        result = await sign_text(result_text)
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


async def split_file_by_size(input_path: str, chunk_length_ms:59000) -> List[str]:
    # Load the input audio file
    audio = AudioSegment.from_file(input_path)

    num_chunks = math.ceil(len(audio) / chunk_length_ms)

    # Split the audio into chunks
    chunks = [audio[i*chunk_length_ms:min((i+1)*chunk_length_ms, len(audio))] for i in range(num_chunks)]
    names = [f"{input_path[:-4]}_chunk_{i}.opus" for i in range(len(chunks))]
    print('CHUNKS:', len(chunks))
    for i, chunk in enumerate(chunks):
        chunk.export(names[i], format="opus")
    return names

