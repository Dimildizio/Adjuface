'''
Code to download and save arbitary image style model from tensorhub.
Not meant to be used in prod
'''

import tensorflow_hub as hub
import tensorflow as tf
from PIL import Image
import numpy as np


model_url = 'https://tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2'
model_dir = 'models'

cycle_gan = hub.load(model_url)
tf.saved_model.save(cycle_gan, model_dir)
loaded_model = tf.saved_model.load(model_dir)
print(loaded_model)


def preprocess_image(image_path):
    img = tf.io.read_file(image_path)
    img = tf.image.decode_image(img, channels=3)
    img = tf.image.convert_image_dtype(img, tf.float32)
    img = img[tf.newaxis, :]
    return img



if __name__ == "__main__":
    style_image_path = 'lisafacebig.png'
    style_image = preprocess_image(style_image_path)
    seg_img = preprocess_image('face.png')
    stylized_image = loaded_model(tf.constant(seg_img), tf.constant(style_image))[0]
    stylized_image = np.squeeze(stylized_image.numpy() * 255).astype(np.uint8)
    image_to_save = Image.fromarray(stylized_image)

    image_to_save.save('output_stylized_image.png', format='PNG')
