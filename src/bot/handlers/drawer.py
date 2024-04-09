import requests
import json
from PIL import Image
from io import BytesIO
import base64
from utils import generate_filename
from bot.handlers.constants import SD_API, SD_URL, SD_FOLDERNAME
from googletrans import Translator


async def translate_prompt(prompt):
    g = Translator()
    text = g.translate(prompt, dest='en').text
    return text


async def request_sd(prompt):
    prompt = await translate_prompt(prompt)
    payload = json.dumps({"prompt": "draw a detailed and realistic image." + prompt, "steps": 100})
    headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + SD_API}
    response = requests.request("POST", SD_URL, headers=headers, data=payload)
    if response.status_code == 200:
        return await save_sd(response)


async def save_sd(response):
    base64_string = response.json()['images'][0]
    image_data = base64.b64decode(base64_string)
    image_bytes = BytesIO(image_data)
    image = Image.open(image_bytes)
    name = await generate_filename(folder=SD_FOLDERNAME)
    image.save(name)
    return name