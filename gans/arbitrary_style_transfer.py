import tensorflow as tf
from PIL import Image
import numpy as np


loaded_model = tf.saved_model.load('models')


def preprocess_image(image_path):
    img = tf.io.read_file(image_path)
    img = tf.image.decode_image(img, channels=3)
    img = tf.image.convert_image_dtype(img, tf.float32)
    img = img[tf.newaxis, :]
    return img


def transfer_style(content_img='face.png', style_image_path='lisafacebig.png'):
    style_image = preprocess_image(style_image_path)
    seg_img = preprocess_image(content_img)

    stylized_image = loaded_model(tf.constant(seg_img), tf.constant(style_image))[0]
    stylized_image = np.squeeze(stylized_image.numpy() * 255).astype(np.uint8)
    return stylized_image

    image_to_save = Image.fromarray(stylized_image)
    image_to_save.save('output_stylized_image.png', format='PNG')


