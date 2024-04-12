import asyncio
import requests
import json
from PIL import Image, UnidentifiedImageError
from io import BytesIO
import base64
from utils import generate_filename
from bot.handlers.constants import SD_API, SD_URL, SD_FOLDERNAME, SD_SLEEP, SD_TRIES, PREPROMPT
from googletrans import Translator


async def translate_prompt(prompt):
    g = Translator()
    text = g.translate(prompt, dest='en').text
    return text


async def get_sd_response(headers, payload):
    response = requests.request("POST", SD_URL, headers=headers, data=payload)
    if response.status_code == 200:
        return await save_sd(response)


async def request_sd(prompt):

    prompt = await translate_prompt(prompt)
    payload = json.dumps({"prompt": PREPROMPT + prompt, "steps": 100})
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + SD_API}
    result = await get_sd_response(headers, payload)
    print('SD result: ', result)

    times = 0
    while (times := times + 1) < SD_TRIES and not result:
        print(f'{times}: {result}')
        await asyncio.sleep(SD_SLEEP)
        result = await get_sd_response(headers, payload)
    return result


async def save_sd(response):
    base64_string = response.json()['images'][0]
    image_data = base64.b64decode(base64_string)
    image_bytes = BytesIO(image_data)
    try:
        image = Image.open(image_bytes)
        name = await generate_filename(folder=SD_FOLDERNAME)
        image.save(name)
        print('SD all ok')
        return name
    except UnidentifiedImageError:
        print(f'SD is sleeping. Response len: {len(base64_string)}\n')
        return False
