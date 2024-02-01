import cv2
import os

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI,  Form
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
from PIL import Image, ImageFont, ImageDraw

WATERMARK = '@dimildiziotrybot'
app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],  # Allows all origins
                   allow_credentials=True,
                   allow_methods=["*"],  # Allows all methods
                   allow_headers=["*"],)  # Allows all headers

# TODO: Currently the access to target images is done this way, however, after using DOcker it will not be an option
ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
get_targets = lambda name: ROOTDIR + '\\target_images\\'+ name
targets_list = {'1': get_targets('peter.png'),
                '2': get_targets('kate.png'),
                '3': get_targets('mona_lisa.png'),
                '4': get_targets('stroganoff.png'),
                '5': get_targets('Emperor-of-Mankind.jpg'),
                '6': get_targets('sororitas.png'),
                '7': get_targets('cyber.png'),
                '8': get_targets('cybergirl.png'),
                '9': get_targets('anime.png'),
                '10': get_targets('anime_girl.png'),
                '11': get_targets('ken.png'),
                '12': get_targets('barbie.png')}
loaded_targets = {num: cv2.imread(name) for num, name in targets_list.items()}


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


async def add_watermark_cv(image, watermark_text=WATERMARK):
    font = cv2.FONT_HERSHEY_PLAIN
    font_scale = 1
    color = (255, 255, 255)
    thickness = 1
    text_size = cv2.getTextSize(watermark_text, font, font_scale, thickness)[0]
    padding = 2
    position = (padding, image.shape[0] - padding - text_size[1])
    shadow_position = (position[0] + 1, position[1] + 1)
    cv2.putText(image, watermark_text, shadow_position, font, font_scale, (0, 0, 0), thickness)
    cv2.putText(image, watermark_text, position, font, font_scale, color, thickness)


async def swap_faces(source_path, mode='1'):
    target_path = targets_list[mode]
    source_faces = load_face(SWAPP, source_path)
    target_face = load_face(SWAPP, target_path)[0]
    result_img = loaded_targets[mode].copy()
    result_faces = []
    try:
        for num, face in enumerate(source_faces):
            result_img = SWAPPER.get(result_img, target_face, face, paste_back=True)
            await add_watermark_cv(result_img)
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


async def get_face(temp_file, mode):
    imgs = await swap_faces(temp_file, mode=mode)
    saved_files = []
    if imgs is None or len(imgs) == 0:
        imgs = [await get_no_face(temp_file)]
    for i, img in enumerate(imgs):
        name = get_n_name(temp_file, i)
        root_dir = ROOTDIR+'/temp/result'
        name = os.path.join(root_dir, os.path.basename(name))
        img.save(name, format='PNG')
        saved_files.append(name)
    return saved_files


@app.post('/insighter')
async def extract_face(file_path: str = Form(...), mode: str = Form(...)):
    saved_faces = await get_face(file_path, mode)
    return saved_faces


def get_n_name(name, n):
    return f'{name[:-4]}_{n}.png'


SWAPP = get_swapp()
SWAPPER = get_swapper()
