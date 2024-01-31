import cv2
import os

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI,  Form
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
from PIL import Image, ImageFont, ImageDraw


app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],  # Allows all origins
                   allow_credentials=True,
                   allow_methods=["*"],  # Allows all methods
                   allow_headers=["*"],)  # Allows all headers

mona_lisa = 'ken.png'


def get_swapp():
    swapp = FaceAnalysis(name='buffalo_l')
    swapp.prepare(ctx_id=0, det_size=(640, 640))
    return swapp


def get_swapper():
    return get_model('inswapper_128.onnx', download=False)


def load_face(swapp, img_path):
    read_img = cv2.imread(img_path)
    faces = swapp.get(read_img)
    return faces


async def swap_faces(source_path, target_path=mona_lisa):
    source_faces = load_face(SWAPP, source_path)
    target_face = load_face(SWAPP, target_path)[0]
    result_img = target_img.copy()
    result_faces = []
    try:
        for num, face in enumerate(source_faces):
            result_img = SWAPPER.get(result_img, target_face, face, paste_back=True)
            result_faces.append(Image.fromarray(cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB)))
    except Exception as e:
        print('EXCEPTION', e)
        return None
    return result_faces


async def get_no_face(original_image_path):
    original_image = Image.open(original_image_path)
    white_canvas = Image.new("RGB", original_image.size, "white")
    draw = ImageDraw.Draw(white_canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 50)
    except IOError:
        font = ImageFont.load_default()
    text = "Чо с еблом?"
    text_width = font.getlength(text)  # draw.textbbox((0,0))text, font=font)
    text_x = (white_canvas.width - text_width) // 2
    text_y = white_canvas.height // 2 - 10
    draw.text((text_x, text_y), text, fill="black", font=font)
    return white_canvas


async def get_face(temp_file):
    imgs = await swap_faces(temp_file, target_path=mona_lisa)
    saved_files = []
    if imgs is None or len(imgs) == 0:
        imgs = [await get_no_face(temp_file)]
    for i, img in enumerate(imgs):
        name = get_n_name(temp_file, i)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/temp/result'
        name = os.path.join(root_dir, os.path.basename(name))
        img.save(name, format='PNG')
        saved_files.append(name)
    return saved_files


@app.post('/insighter')
async def extract_face(file_path: str = Form(...)):
    saved_faces = await get_face(file_path)
    return saved_faces


def get_n_name(name, n):
    return f'{name[:-4]}_{n}.png'


target_img = cv2.imread(mona_lisa)  # upload once
SWAPP = get_swapp()
SWAPPER = get_swapper()
