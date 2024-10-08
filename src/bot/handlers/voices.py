"""
Module for handling voice-related functionalities including speech synthesis and recognition.

This module provides functions to handle voice messages, including downloading, splitting, recognizing, and
responding with recognized text.
It also offers speech synthesis functionalities to convert text to speech using an API.

Key Features:
- Handling voice messages: Functions to download, split, recognize, and respond with recognized text from voice
messages.
- Speech synthesis: Functionality to convert text to speech using an API.

Usage:
- Use the `handle_voice` function to handle messages containing voice files. This function downloads the voice
file, recognizes speech, and responds with the recognized text.
- The `synthesize_speech` function can be used to synthesize speech from text. Specify the text, voice, and
desired file extension.


Functions:
- handle_voice(message: Message, token: str): Handles a message containing a voice file by downloading,
  recognizing, and responding with the recognized text.
- split_and_recognize(input_path: str) -> List[str]: Splits the input audio file into chunks, recognizes
  speech in each chunk, and returns a list of recognized texts.
- recognize_speech(input_path: str) -> Optional[Dict[str, Any]]: Recognizes speech in the audio file located at
  the given input path using an API.
- download_voice_file(message: Message, token: str) -> Optional[str]: Downloads the voice file from the message
  and saves it locally.
- respond_with_recognized_text(message: Message, recognized_texts: List[str]) -> None: Responds to the message
  with recognized text.
- sign_text(text: List[str]) -> str: Signs the recognized text with additional information.
- get_api_access() -> str: Retrieves the API access token for text-to-speech services.
- split_file_by_size(input_path: str, chunk_length_ms: int = 59000) -> List[str]: Splits the input audio file
  into chunks based on the specified chunk length.
- synthesize_speech(text: str, voice: str = 'Bys_24000', ext: str = 'opus') -> Optional[str]: Synthesizes speech
  from the given text using the specified voice and file extension.
"""


import aiohttp
import uuid
import math
import os

from aiofiles import open as aio_open
from aiogram.types import Message
from pydub import AudioSegment
from typing import List, Optional

from bot.handlers.checks import is_premium
from bot.handlers.constants import TGBOT_PATH, TTS_AUTH, TTS_TOKEN, TTS_LINK, STT_LINK, TGBOT_NAME, TTS_AUDIO_SIZE
from utils import generate_filename


async def handle_voice(message: Message, token: str):
    """
    Handles a message containing a voice file by downloading, recognizing, and responding with the recognized text.

    :param message: The message containing the voice file.
    :param token: Token for premium access.
    :return: None
    """
    if not await is_premium(message):
        return
    input_path = await download_voice_file(message, token)
    if input_path:
        recognized_data = await split_and_recognize(input_path)
        await respond_with_recognized_text(message, recognized_data)


async def get_voice_tone(recognized_data, perform=False):
    emotion = []
    if perform:
        emotions = recognized_data.get("emotions", ["----Could not recognize emotions----"])
        emotion = [',\n'.join([f"{key}: {round(value, 3)}"
                                      for key, value in emotions[0].items()])]
    return emotion



async def split_and_recognize(input_path: str) -> List:
    """
    Splits the input audio file into chunks, recognizes speech in each chunk,
    and returns a list of recognized texts.

    :param input_path: The file path of the input audio.
    :return: A list of recognized texts.
    """
    chunks_paths = await split_file_by_size(input_path, TTS_AUDIO_SIZE)
    recognized_texts = []
    for chunk_path in chunks_paths:
        recognized_data = await recognize_speech(chunk_path)
        if recognized_data:
            recognized_text = recognized_data.get("result", ["----Could not recognize text----"])

            recognized_texts.extend(recognized_text)
            emotions =  await get_voice_tone(recognized_data, perform=False)
            recognized_texts.extend(emotions)
            os.remove(chunk_path)
            print(f'{chunk_path} recognized')
        else:
            print(f'we got problem {chunk_path}')
    print('RESULT:', recognized_texts)
    return recognized_texts


async def recognize_speech(input_path: str) -> Optional:
    """
    Recognizes speech in the audio file located at the given input path using an API.

    :param input_path: The file path of the audio file to be recognized.
    :return: A dictionary containing the recognized speech data, or None if recognition fails.
    """
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


async def download_voice_file(message: Message, token: str) -> Optional[str]:
    """
    Downloads the voice file from the message and saves it locally.

    :param message: The message containing the voice file.
    :param token: The token for accessing the file.
    :return: The file path of the downloaded voice file, or None if download fails.
    """
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


async def respond_with_recognized_text(message: Message, recognized_texts: List[str]) -> None:
    """
    Responds to the message with recognized text.

    :param message: The message to respond to.
    :param recognized_texts: A list of recognized text strings.
    :return: None
    """

    if recognized_texts:
        text = ''.join(recognized_texts)
        chunk_size = 4000  # Adjust the chunk size as needed
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        for chunk in chunks:
            #result = await sign_text(chunk)
            print(f"Recognized text: {chunk}")
            await message.answer(chunk)
    else:
        print("Failed to recognize speech.")
        await message.answer("Failed to recognize speech.")


async def sign_text(text: List) -> str:
    """
    Signs the recognized text with additional information.

    :param text: A list of recognized text strings.
    :return: The signed text.
    """
    text = '\n\n'.join(text)
    # change response for translation from config's LOCALIZATION
    return f'Текст вашего сообщения:\n\n{text}\n\nРаспознано с @{TGBOT_NAME}'.replace('. ', '.\n')


async def get_api_access() -> str:
    """
    Retrieves the API access token for text-to-speech services.

    :return: The access token.
    """
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


async def split_file_by_size(input_path: str, chunk_length_ms: int = 59000) -> List[str]:
    """
    Splits the input audio file into chunks based on the specified chunk length.

    :param input_path: The file path of the input audio file.
    :param chunk_length_ms: The length of each chunk in milliseconds (default is 59000 ms).
    :return: A list of file paths for the generated audio chunks.
    """
    audio = AudioSegment.from_file(input_path)

    num_chunks = math.ceil(len(audio) / chunk_length_ms)

    # Split the audio into chunks
    chunks = [audio[i*chunk_length_ms:min((i+1)*chunk_length_ms, len(audio))] for i in range(num_chunks)]
    names = [f"{input_path[:-4]}_chunk_{i}.opus" for i in range(len(chunks))]
    print('CHUNKS:', len(chunks))
    for i, chunk in enumerate(chunks):
        chunk.export(names[i], format="opus")
    return names


async def synthesize_speech(text: str, voice: str = 'Bys_24000', ext: str = 'opus'):
    """
    Synthesizes speech from the given text using the specified voice and file extension.

    :param text: The text to synthesize.
    :param voice: The voice to use for synthesis (default is 'Bys_24000').
    :param ext: The file extension for the synthesized audio (default is 'opus').
    :return: The file path of the synthesized audio, or None if synthesis fails.
    """
    access_token = await get_api_access()
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/text'}
    params = {'format': ext, 'voice': voice}

    async with aiohttp.ClientSession() as session:
        async with session.post(TTS_LINK, headers=headers, params=params, data=text.encode('utf-8')) as response:
            if response.status == 200:
                output_path = await generate_filename('voice', 'audio', 'opus')
                async with aio_open(output_path, 'wb') as audio_file:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        await audio_file.write(chunk)
                return output_path
            else:
                return
