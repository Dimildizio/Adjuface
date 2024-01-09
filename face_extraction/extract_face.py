import cv2
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File
from tempfile import NamedTemporaryFile
import os
import io
from ultralytics import YOLO
import torch


file_db = {}  # TODO: change for real db
app = FastAPI()
app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],  # Allows all origins
                   allow_credentials=True,
                   allow_methods=["*"],  # Allows all methods
                   allow_headers=["*"],)  # Allows all headers


@app.get("/images/{file_id}")  # for tests
async def get_image(file_id: str):
    file_path = file_db.get(file_id)
    if file_path:
        return FileResponse(file_path)
    return {"error": "File not found"}


@app.post('/extract_face')
async def extract_face(file: UploadFile = File(...)):
    with NamedTemporaryFile(delete=False, suffix='.jpg') as tempfile:
        contents = await file.read()
        tempfile.write(contents)

    filename = tempfile.name
    new_filename = filename.replace('.jpg', '_modified.png')

    await get_face(filename, new_filename)

    #  TODO: could just send Image file
    img = Image.open(new_filename)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    return StreamingResponse(io.BytesIO(img_byte_arr), media_type="image/png")



def predict(model, img, size=(640, 640)):
    image_tensor = torch.from_numpy(np.array(img.resize(size))).float().div(255).permute(2, 0, 1).unsqueeze(0)
    prediction = model(image_tensor)
    return prediction[0].masks


def cutout_first_mask(img, masks):
            # Use only the first mask
            #if len(masks) > 0:
            first_mask = masks[0].data[0].cpu().numpy()
            mask_resized = cv2.resize(first_mask, (img.width, img.height))
            segmented_image = get_seg_mask(img, mask_resized)
            return segmented_image
            #return None

def apply_mask_to_image(img, masks, coordinates=(191, 83, 247, 267), base_image_path='mona_lisa.png'):
        mask=cutout_first_mask(img, masks)
        mask = np.array(mask)[:, :, 3] / 255.0
        base_image = cv2.imread(base_image_path)
        x1, y1, x2, y2 = coordinates
        ask_resized = cv2.resize(mask, (x2 - x1, y2 - y1))
        for i in range(3):  # Assuming base image is in BGR format
            base_image[y1:y2, x1:x2, i] = base_image[y1:y2, x1:x2, i] * (1 - mask_resized) + mask_resized * 255
        return Image.fromarray(cv2.cvtColor(base_image, cv2.COLOR_BGR2RGB))

def combine_masks(image, masks):
    combined_mask = np.zeros((image.height, image.width))
    for msk in masks:
        mask_np = msk.data[0].cpu().numpy()
        mask_resized = cv2.resize(mask_np, (image.width, image.height))
        combined_mask = np.maximum(combined_mask, mask_resized)
    return combined_mask


def cutout(img, masks):
    combined_mask = combine_masks(img, masks)
    segmented_image = get_seg_mask(img, combined_mask)
    return segmented_image

def get_seg_mask(img, combi_mask):
    image_rgba = img.convert("RGBA")
    data = np.array(image_rgba)
    alpha_channel = (combi_mask * 255).astype(np.uint8)
    data[..., 3] = alpha_channel
    segmented_image = Image.fromarray(data)
    return segmented_image


def get_no_face(original_image):
    # Create a white canvas of the same size as the original image
    white_canvas = Image.new("RGB", original_image.size, "white")
    # Optionally, add text "No face" on it
    draw = ImageDraw.Draw(white_canvas)
    try:
        # Use a truetype font if available, otherwise default to a simple font
        font = ImageFont.truetype("arial.ttf", 50)
    except IOError:
        font = ImageFont.load_default()
    text = "Чо с еблом?"
    text_width, text_height = draw.textsize(text, font=font)
    text_x = (white_canvas.width - text_width) // 2
    text_y = (white_canvas.height - text_height) // 2
    draw.text((text_x, text_y), text, fill="black", font=font)
    return white_canvas


async def get_face(temp_file, new_file):
    weights = 'seg_models/heads_weights.pt'
    seg_model = YOLO(weights)
    image = Image.open(temp_file)
    masks = predict(seg_model, image)
    segmented_img =  apply_mask_to_image(image,masks)  # cutout(image, masks) if masks else get_no_face(image)
    segmented_img.save(new_file, format="PNG")
    print('new file saved')
    return segmented_img


