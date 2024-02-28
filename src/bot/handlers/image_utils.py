"""
This module provides the core functionalities for handling image processing requests within the Telegram bot.
It encompasses the steps from receiving an image from the user, preparing it for processing, interacting with
the FastAPI-based face swapping service, and managing the response, including saving and sending the processed
images back to the user.

Key Functionalities:
- Preparation of images for processing, including fetching the image from Telegram and generating file paths.
- Sending image processing requests to the FastAPI service and handling the responses.
- Downloading and saving processed images, then sending them back to the users with appropriate captions.
- Error handling for failed image processing or download attempts, ensuring users are informed of issues.

Usage:
- Functions in this module are designed to be called during the bots handling of user-submitted images for
  face swapping. They manage the technical aspects of image processing, from initial receipt to final presentation
  of the swapped images.

Example:
- Upon receiving a photo submission, the bot calls `handle_image_constants` to prepare the image, followed by
  `image_handler_logic` to manage the processing workflow, which may involve `image_handler_swapper` for sending
  the image to the processing service and `handler_image_send` for presenting the results to the user.

Dependencies:
- aiohttp: For asynchronous HTTP requests to the image processing service.
- Aiogram: For interactions with Telegram's API, including fetching images and sending messages or photos.
- Application-specific utilities: For generating filenames, saving images locally, and accessing bot settings.
"""


import aiohttp
import json

from aiogram.types import Message, FSInputFile
from typing import Any, Tuple, List
from utils import generate_filename, save_img

from bot.database.db_logging import log_input_image_data, log_output_image_data, log_error
from bot.database.db_fetching import fetch_user_data
from bot.database.db_users import decrement_requests_left
from bot.handlers.checks import check_limit, target_image_check
from bot.handlers.constants import TGBOT_PATH, LOCALIZATION, CONTACTS, FACE_EXTRACTION_URL


async def handle_image_constants(message: Message, token: str, user: Any) -> Tuple[str, str]:
    """
    Handles constants related to image processing.

    :param message: The message with user data.
    :param token: The Telegram bot token.
    :param user: User data.
    :return: File URL and input path.
    """
    file_path = await message.bot.get_file(message.photo[-1].file_id)
    file_url = f"{TGBOT_PATH}{token}/{file_path.file_path}"
    input_path = await generate_filename('target_images' if user.receive_target_flag else 'original')
    await log_input_image_data(message, input_path)
    return file_url, input_path


async def handler_image_send(message: Message, output_paths: List) -> bool:
    """
    Handles sending processed images.

    :param message: The message with user data.
    :param output_paths: List of output image paths.
    :return: True if successful, else False.
    """
    for output_path in output_paths:
        user = await fetch_user_data(message.from_user.id)
        if not (await check_limit(user, message)):
            return False
        inp_file = FSInputFile(output_path)
        await message.answer_photo(photo=inp_file,
                                   caption=LOCALIZATION['captions'].format(bot_name=CONTACTS['bot_name']))
        print('Image sent')
    return True


async def image_handler_received_result(message: Message, user: Any, response: aiohttp.ClientResponse,
                                        input_path: str) -> bool:
    """
    Handles the result of image processing when received successfully.

    :param message: The message with user data.
    :param user: User data.
    :param response: The response from the processing request.
    :param input_path: The input image path.
    :return: True if successful, False otherwise.
    """
    image_paths = json.loads(await response.text())
    await log_output_image_data(message, input_path, image_paths)  # logging to db
    if not await handler_image_send(message, image_paths):
        return False
    await decrement_requests_left(user.user_id, n=len(image_paths))
    await message.answer(LOCALIZATION['attempts_left'].format(
        limit=max(0, user.requests_left - len(image_paths))))
    return True


async def image_handler_result_failed(message: Message, response: aiohttp.ClientResponse) -> None:
    """
    Handles the case when the result of image processing failed.

    :param message: The message with user data.
    :param response: The response from the processing request.
    :return: None
    """
    error_message = await response.text()
    print(error_message)
    await message.answer(LOCALIZATION)


async def image_handler_swapper(message: Message, user: Any, session: aiohttp.ClientSession, input_path: str) -> bool:
    """
    Handles FASTAPI interaction for swapping of faces.

    :param message: The message with user data.
    :param user: User data.
    :param session: The aiohttp client session.
    :param input_path: The input image path.
    :return: True if successful, False otherwise.
    """
    async with session.post(FACE_EXTRACTION_URL,
                            data={'file_path': input_path, 'mode': user.mode}
                            ) as response:

        print('Sending image path through fastapi')
        if response.status == 200:
            if not await image_handler_received_result(message, user, response, input_path):
                return False
        else:
            await image_handler_result_failed(message, response)
        return True


async def image_handler_load(message: Message, user: Any, response: aiohttp.ClientResponse, input_path: str) -> bool:
    """
    Handles downloading of images.

    :param message: The message with user data.
    :param user: User data.
    :param response: The response from the download request.
    :param input_path: The input image path.
    :return: True if successful, False otherwise.
    """
    content = await response.read()
    await message.answer(LOCALIZATION['img_received'])
    await save_img(content, input_path)
    print('Image downloaded')
    return await target_image_check(message, user, input_path)


async def image_handler_download_failed(message: Message, response: aiohttp.ClientResponse) -> None:
    """
    Handles the case when image download failed.

    :param message: The message with user data.
    :param response: The response from the download request.
    :return: None
    """
    error_message = await response.text()
    print(error_message)
    await message.answer(LOCALIZATION['failed'])


async def image_handler_logic(message, user, file_url, input_path):
    """
    Handles all image interaction logic

    1. Downloads the image from Telegram using the provided bot token.
    2. Generates an input file path and logs input image data.
    3. Initiates processing of the image through FastAPI.
    4. Handles various responses from the processing:
       - If the image is successfully downloaded, it is saved, and target image checks are performed.
       - If the processed image paths are received, they are logged and sent as photo messages to the user.
       - Limits on user requests are updated and notifications are sent to the user.
    5. In case of any exceptions or errors during the process, appropriate error messages are sent.

    :param message: The message with user data.
    :param user: User data.
    :param file_url: The url to download a file from tg.
    :param input_path: The input image path.
    :return: None
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as response:
            if response.status == 200:
                if await image_handler_load(message, user, response, input_path):
                    return
            else:
                await image_handler_download_failed(message, response)
                return
        await image_handler_swapper(message, user, session, input_path)
