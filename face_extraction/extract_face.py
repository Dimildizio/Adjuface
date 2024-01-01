import cv2
import numpy as np
from PIL import Image
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File
from tempfile import NamedTemporaryFile
import os, io


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
    new_filename = filename.replace('.jpg', '_modified.jpg')

    await get_face(filename, new_filename)
    img = Image.open(new_filename)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    return StreamingResponse(io.BytesIO(img_byte_arr), media_type="image/jpeg")


    file_id = os.path.basename(new_filename)
    file_db[file_id] = new_filename
    print(file_db)
    return {'file_id': file_id}


async def get_face(temp_file, new_file):
    image = Image.open(temp_file)
    img_cv = np.array(image)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))
    for (x, y, w, h) in faces:
        cv2.rectangle(img_cv, (x, y), (x + w, y + h), (0, 255, 0), 2)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img_cv, 'face', (x, y - 10), font, 0.9, (0, 255, 0), 2, cv2.LINE_AA)
    image = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
    image.save(new_file)
    print('new file saved')
    return image
