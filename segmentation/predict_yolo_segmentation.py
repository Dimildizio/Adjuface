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


def combine_masks(image, masks):
    combined_mask = np.zeros((image.height, image.width))
    for msk in masks:
        mask_np = msk.data[0].cpu().numpy()
        mask_resized = cv2.resize(mask_np, (image.width, image.height))
        combined_mask = np.maximum(combined_mask, mask_resized)
    return combined_mask


def overlay(img, masks):
    combined_mask = combine_masks(img, masks)
    plt.imshow(np.array(img))
    plt.imshow(combined_mask, cmap='gray', alpha=0.5)
    plt.axis('off')


def cutout_and_plot(img, msks):
    """Monitor issue with creating too many masks"""
    num_masks = len(msks)
    masks_per_row = 4
    num_rows = math.ceil(num_masks / masks_per_row)

    fig, axs = plt.subplots(num_rows, masks_per_row, figsize=(12, 6))
    axs = axs.flatten() if num_masks > 1 else [axs]

    for i, msk in enumerate(msks):
        mask_np = msk.data[0].cpu().numpy().squeeze()
        mask_resized = cv2.resize(mask_np, (image.width, image.height))
        segmented_image = get_seg_mask(img, mask_resized)

        axs[i].imshow(segmented_image)
        axs[i].set_xticks([])
        axs[i].set_yticks([])
        axs[i].set_facecolor('gray')


def cutout(img, masks):
    combined_mask = combine_masks(img, masks)
    segmented_image = get_seg_mask(img, combined_mask)
    plt.imshow(segmented_image)
    plt.axis('off')
    return segmented_image

def get_seg_mask(img, combi_mask):
    image_rgba = img.convert("RGBA")
    data = np.array(image_rgba)
    alpha_channel = (combi_mask * 255).astype(np.uint8)
    data[..., 3] = alpha_channel
    segmented_image = Image.fromarray(data)
    return segmented_image


def combine_largest_mask(masks, image_size):
    largest_area = 0
    largest_mask = None
    for msk in masks:
        mask_np = msk.data[0].cpu().numpy()
        mask_resized = cv2.resize(mask_np, image_size)
        area = np.sum(mask_resized > 0)  # Calculate the area (sum of all positive pixels)
        if area > largest_area:
            largest_area = area
            largest_mask = mask_resized
    return largest_mask


def cutout_largest_mask(img, masks):
    image_size = (img.width, img.height)
    largest_mask = combine_largest_mask(masks, image_size)
    cutout_image = get_seg_mask(img, largest_mask)
    plt.imshow(cutout_image)
    plt.axis('off')


def plot_img(img, msk, task=''):
    if task == 'overlay':
        overlay(img, msk)
    elif task == 'masks':
        cutout_and_plot(img, msk)
    elif task == 'largest':
        cutout_largest_mask(img, msk)
    else:
        cutout(img, msk)
    plt.show()


def get_image(image_path):
    return Image.open(image_path).convert('RGB')


if __name__ == '__main__':
    target_photo = 'datasets/photo1.jpg'
    weights = 'seg_models/heads_weights.pt'
    seg_model = YOLO(weights)
    image = get_image(target_photo)
    mask = predict(seg_model, image)
    for mode in ('masks', 'cutout', 'overlay', 'largest'):
        plot_img(image, mask, mode)
