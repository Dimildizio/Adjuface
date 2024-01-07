import numpy as np
import matplotlib.pyplot as plt
import cv2
import torch
from PIL import Image
from ultralytics import YOLO
import math


def predict(model, img, size=(640, 640)):
    image_tensor = torch.from_numpy(np.array(img.resize(size))).float().div(255).permute(2, 0, 1).unsqueeze(0)
    prediction = model(image_tensor)
    print(len(prediction[0].masks))
    return prediction[0].masks


def combine_masks(masks):
    combined_mask = np.zeros((image.height, image.width))
    for msk in masks:
        mask_np = msk.data[0].cpu().numpy()
        mask_resized = cv2.resize(mask_np, (image.width, image.height))
        combined_mask = np.maximum(combined_mask, mask_resized)
    return combined_mask


def overlay(img, masks):
    combined_mask = combine_masks(masks)
    plt.imshow(np.array(img))
    plt.imshow(combined_mask, cmap='gray', alpha=0.5)
    plt.axis('off')


def cutout(img, masks):
    combined_mask = combine_masks(masks)
    image_rgba = img.convert("RGBA")
    data = np.array(image_rgba)
    alpha_channel = (combined_mask * 255).astype(np.uint8)
    data[..., 3] = alpha_channel
    segmented_image = Image.fromarray(data)
    plt.imshow(segmented_image)
    plt.axis('off')


def plot_img(img, msk, task=''):
    if task == 'overlay':
        overlay(img, msk)
    else:
        cutout(img, msk)

    plt.show()


def get_image(image_path):
    return Image.open(image_path).convert('RGB')


if __name__ == '__main__':
    target_photo = 'photo.png'
    weights = 'seg_models/heads_weights.pt'
    seg_model = YOLO(weights)
    image = get_image(target_photo)
    mask = predict(seg_model, image)
    plot_img(image, mask, 'masks')
