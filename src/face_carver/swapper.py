"""
This module `swapper.py` utilizes computer vision and face analysis technologies to swap faces in images.
It leverages the FastAPI framework for serving a REST API, InsightFace for face detection and analysis,
and OpenCV for image manipulation. The module supports swapping faces between a source image and predefined
target images, adding watermarks to processed images, and handling requests with CORS policies for web
integration.

Features include:
- Loading and processing images for face detection and swapping.
- Dynamically selecting target images for face swapping based on user input.
- Adding custom watermarks to images to indicate processing.
- Serving a REST API endpoint for face swapping operations.
- Utilizing InsightFace for advanced face analysis and detection.
- Employing OpenCV for image reading, writing, and transformations.

The FastAPI application is configured to handle cross-origin requests, allowing integration
with front-end applications from different origins. The face swapping process involves detecting faces
in source images, selecting appropriate target faces, and applying the swap.
If no faces are detected, a custom message is generated on the image.

Usage:
- Run the FastAPI application and send POST requests to the `/swapper` endpoint with an image file path
and a mode specifying the target face. The API returns paths to the processed images with swapped faces.

Dependencies:
- FastAPI: For serving the API and handling requests.
- InsightFace: For face detection and analysis.
- OpenCV (cv2): For image manipulation tasks.
- Pillow (PIL): For additional image processing capabilities, especially for watermarking and message
  generation on images.

The module is designed to be extensible, allowing for additional functionalities such as adding
more target faces to json file, modifying watermark text and style, and enhancing face swapping algorithms.

Example:
    To swap faces in an image, send a POST request to `/swapper` with the image file path and mode.
    The server processes the image and returns paths to the resulting images.

Note:
    Before deploying or using this module in a production environment, ensure all dependencies are installed
    and the application is properly configured, especially the paths to target images and the database for
    storing processed images.
"""


import cv2
import os
import json

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Form, HTTPException
from insightface.app import FaceAnalysis
from insightface.model_zoo import get_model
from PIL import Image, ImageFont, ImageDraw
from typing import Any, Dict, List, Tuple, Optional


# Define root dir and watermark
ROOTDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATERMARK = '@Adjuface_bot'

# Run FastAPI application with middleware
app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],  # Allows all origins
                   allow_credentials=True,
                   allow_methods=["*"],  # Allows all methods
                   allow_headers=["*"],)  # Allows all headers


async def get_n_name(name: str, n: int) -> str:
    """
    Generates a new filename by appending a number to the original filename.

    :param name: The original filename.
    :param n: The number (equal to the n-th face of original image faces) to append to the filename.
    :return: A new filename with the number appended before the file extension.
    """
    return f'{name[:-4]}_{n}.png'


def load_target_names() -> Dict[str, str]:
    """
    Loads target image names and their paths from a JSON file.

    :return: A dictionary mapping modes to image file paths.
    """
    with open(ROOTDIR + '\\target_images_en.json', 'r') as file:
        cats = json.load(file)
    modes_n_paths = {}
    for cat, items in cats['categories'].items():
        for item in items:
            modes_n_paths[item['mode']] = item['filepath']
    return modes_n_paths


# Load target modes, paths and images to RAM
targets_list = load_target_names()
loaded_targets = {mode: cv2.imread(img_path) for mode, img_path in targets_list.items()}


def get_swapp() -> FaceAnalysis:
    """
    Initializes, prepares size and returns a FaceAnalysis object for face detection and analysis.

    :return: A FaceAnalysis object configured for use.
    """
    swapp = FaceAnalysis(name='buffalo_l')
    swapp.prepare(ctx_id=0, det_size=(640, 640))
    return swapp


def get_swapper() -> Any:
    """
    Loads and returns a face swapping model.

    :return: A model object for face swapping.
    """
    return get_model('inswapper_128.onnx', download=False)


async def load_face(swapp: FaceAnalysis, img_path: str) -> List:
    """
    Loads a face from an image file using a given FaceAnalysis object.

    :param swapp: A FaceAnalysis object used for detecting faces.
    :param img_path: The path to the image file.
    :return: Detected faces in the image.
    """
    read_img = cv2.imread(img_path)
    faces = swapp.get(read_img)
    return faces


async def filter_multiple_targets(target_faces: List, n: int = 1) -> List:
    """
    Filters and returns the n faces with the largest bbox sizes.

    :param target_faces: List of detected faces.
    :param n: number of faces to filter
    :return: The n the largest faces.
    """
    if len(target_faces) <= n:
        return target_faces
    sorted_faces = sorted(target_faces, key=lambda face: (face.bbox[2] - face.bbox[0]) * (
                                                          face.bbox[3] - face.bbox[1]), reverse=True)
    return sorted_faces[:n]


async def add_watermark_cv(image: Any, watermark_text: str = WATERMARK) -> None:
    """
    Adds a watermark to an image. It has shadow to be seen on white and black.

    :param image: The image to which the watermark will be added. "Any" since it's not worth importing ndarray for that.
    :param watermark_text: The text of the watermark. Defaults to a global variable WATERMARK.
    """
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


async def select_target(mode: str) -> Tuple[str, Any]:
    """
    Selects a target image based on the mode (order numbers in json file).

    :param mode: The mode used to select the target image.
    :return: A tuple containing the path to the target image and the image itself in ndarray (Any).
    """
    if len(mode) < 4:
        target_path = targets_list[mode]
        result_img = loaded_targets[mode].copy()
    else:
        target_path = mode
        result_img = cv2.imread(mode)
    return target_path, result_img


async def swap_all_target(source_faces: List, result_img: Any, target_faces: List) -> List:
    """
    Swaps faces for a single target from multiple sorts creating different images

    :param source_faces: Detected faces from user images
    :param result_img: A copy of original target image
    :param target_faces: A from the original target image
    :returns: A list of n images (n = len(source_faces))
    """
    result_faces = []
    for face in source_faces:
        new_result_img = result_img.copy()
        for t_face in target_faces:
            new_result_img = SWAPPER.get(new_result_img, t_face, face, paste_back=True)
            break
        await add_watermark_cv(new_result_img)
        result_faces.append(Image.fromarray(cv2.cvtColor(new_result_img, cv2.COLOR_BGR2RGB)))
        #  if len(result_faces) > n:
        #    break
    return result_faces


async def swap_faces(source_path: str, mode: str = '1') -> Optional[List[Image.Image]]:
    """
    Swaps faces between the source image and the target image specified by mode.

    :param source_path: Path to the source image.
    :param mode: Mode specifying the target image or operation.
    :return: A list of PIL Image objects with swapped faces, or None if an error occurs.
    """
    target_path, result_img = await select_target(mode)
    source_faces = await load_face(SWAPP, source_path)
    target_faces = await load_face(SWAPP, target_path)
    if len(mode) > 4:  # max classes num is 100 longer mode name means custom target
        target_faces = await filter_multiple_targets(target_faces, n=1)
    try:
        if not target_faces or not source_faces:  # if no faces detected in target face
            raise ValueError('No face detected in targets')
        result_faces = await swap_all_target(source_faces, result_img, target_faces)
    except Exception as e:
        print(f'EXCEPTION {type(e).__name__}: {e}')
        return None
    return result_faces


async def get_no_face(original_image_path: str) -> Image.Image:
    """
    Creates an image with a text message "Что с лицом?" when no face is detected in the original image.
    The size of the new image is the same as original image.

    :param original_image_path: Path to the original image that failed face detection.
    :return: A PIL Image object with a custom message indicating no face was detected.
    """
    original_image = Image.open(original_image_path)
    white_canvas = Image.new("RGB", original_image.size, "white")
    draw = ImageDraw.Draw(white_canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 50)
    except IOError:
        font = ImageFont.load_default()
    text = "Что с лицом?"
    text_width = font.getlength(text)  # draw.textbbox((0,0))text, font=font)
    text_x = (white_canvas.width - text_width) // 2
    text_y = white_canvas.height // 2 - 10
    draw.text((text_x, text_y), text, fill="black", font=font)
    return white_canvas


async def get_face(temp_file: str, mode: str) -> List[str]:
    """
    Processes an image file to swap faces and save the resulting images with a watermark.
    If no faces are detected, it generates an image with a predefined message.

    :param temp_file: The path to the file containing the source image.
    :param mode: The mode specifying what target faces should be swapped with.
    :return: A list of PATHS to the saved image files.
    """
    imgs = await swap_faces(temp_file, mode=mode)
    saved_files = []
    if imgs is None or len(imgs) == 0:
        imgs = [await get_no_face(temp_file)]
    for i, img in enumerate(imgs):
        name = await get_n_name(temp_file, i)
        root_dir = ROOTDIR+'/temp/result'
        name = os.path.join(root_dir, os.path.basename(name))
        img.save(name, format='PNG')
        saved_files.append(name)
    return saved_files


@app.post('/swapper')
async def extract_face(file_path: str = Form(...), mode: str = Form(...)) -> List[str]:
    """
    FastAPI endpoint to extract faces from an image file and swap them based on the provided mode.
    The modified image(s) are saved and their PATHS are returned.

    :param file_path: The path to the image file to process.
    :param mode: The mode specifying what target faces should be swapped to.
    :return: A list of PATHS to the saved image files.
    """
    saved_faces = await get_face(file_path, mode)
    return saved_faces


@app.post('/analyze_faces')
async def analyze_faces(file_path: str = Form(...)) -> dict:
    """
    Analyzes faces in the provided image file, returning age, gender, and bounding box information.

    :param file_path: Path to the image file to analyze.
    :return: Dictionary containing detected face information.
    """
    read_img = cv2.imread(file_path)
    if read_img is None:
        raise HTTPException(status_code=400, detail="Invalid file path or unsupported image format")
    faces = SWAPP.get(read_img)
    if not faces:
        return {"message": "No faces detected"}
    results = []
    for face in faces:
        gender = int(face.gender > 0)
        bbox = face.bbox.astype(int).tolist()
        results.append({"age": max(1, face.age-6), "gender": gender, "bbox": bbox})

    return {"faces": results}


# Create instances of detectors and swappers
SWAPP = get_swapp()
SWAPPER = get_swapper()
