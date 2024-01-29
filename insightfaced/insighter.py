import io
import cv2

from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
from PIL import Image, ImageFont, ImageDraw
from tempfile import NamedTemporaryFile


input_img_path = 'img_5147.png'
mona_lisa = 'mona_lisa.png'


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

    img_target = cv2.imread(target_path)  # could remove later
    target_face = SWAPP.get(img_target)[0]
    result_img = target_img.copy()

    try:
        for num, face in enumerate(source_faces):
            result_img = SWAPPER.get(result_img, target_face, face, paste_back=True)
            #  cv2.imwrite(f"face_{num}.jpg", result_img)
            return Image.fromarray(cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB))  # TODO: return multiple images
    except Exception as e:
        print('EXCEPTION', e)
        return None


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


async def get_face(temp_file, new_file):
    img = await swap_faces(temp_file, target_path=mona_lisa)
    if img is None:
        img = await get_no_face(temp_file)
    img.save(new_file, format="PNG")
    print('new file saved')
    return img


target_img = cv2.imread(mona_lisa)
SWAPP = get_swapp()
SWAPPER = get_swapper()
#  get_face(input_img_path, input_img_path[:-4]+'restyled.png')

file_db = {}  # TODO: change for real db
app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],  # Allows all origins
                   allow_credentials=True,
                   allow_methods=["*"],  # Allows all methods
                   allow_headers=["*"],)  # Allows all headers


@app.post('/insighter')
async def extract_face(file: UploadFile = File(...)):
    with NamedTemporaryFile(delete=False, suffix='.jpg') as tempfile:
        contents = await file.read()
        tempfile.write(contents)

    filename = tempfile.name
    new_filename = filename[-4]+'modified.png'  # .replace('.jpg', '_modified.png')

    await get_face(filename, new_filename)
    #  TODO: could just send Image file
    img = Image.open(new_filename)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return StreamingResponse(io.BytesIO(img_byte_arr), media_type="image/png")
