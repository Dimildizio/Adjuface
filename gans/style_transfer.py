import tensorflow as tf
import numpy as np
from PIL import Image

loaded_model = tf.saved_model.load('models')

def preprocess_image(image_path):
    img = tf.io.read_file(image_path)
    img = tf.image.decode_image(img, channels=3)
    img = tf.image.convert_image_dtype(img, tf.float32)
    img = img[tf.newaxis, :]
    return img

def transfer_style(content_img_path, style_image_path):
    style_image = preprocess_image(style_image_path)
    content_img = preprocess_image(content_img_path)

    stylized_image = loaded_model(tf.constant(content_img), tf.constant(style_image))[0]
    stylized_image = np.squeeze(stylized_image.numpy() * 255).astype(np.uint8)
    # Convert to PIL image and return
    return Image.fromarray(stylized_image)
