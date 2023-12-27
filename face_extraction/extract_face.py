import cv2
import numpy as np
from PIL import Image


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
    return image