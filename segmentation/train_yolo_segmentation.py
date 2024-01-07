from ultralytics import YOLO
import torch
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import cv2


def train(model, yaml_path='datasets/data.yaml', epochs=10):
    print(f'Training on {"gpu" if torch.cuda.is_available() else "cpu"}')
    model.train(data=yaml_path, epochs=epochs, imgsz=640, device=0)


def predict(model, image, size = (640, 640)):
    image_tensor = torch.from_numpy(np.array(image.resize(size))).float().div(255).permute(2, 0, 1).unsqueeze(0)
    prediction = model(image_tensor)
    print(len(prediction[0].masks))
    return prediction[0].masks


def combine_masks(masks):
    combined_mask = np.zeros((image.height, image.width))
    for mask in masks:
        mask_np = mask.data[0].cpu().numpy()
        mask_resized = cv2.resize(mask_np, (image.width, image.height))
        combined_mask = np.maximum(combined_mask, mask_resized)
    return combined_mask


def overlay(image, masks):
    combined_mask = combine_masks(masks)
    plt.imshow(np.array(image))
    plt.imshow(combined_mask, cmap='gray', alpha=0.5)


def cutout(image, masks):
    combined_mask = combine_masks(masks)
    image_rgba = image.convert("RGBA")
    data = np.array(image_rgba)
    alpha_channel = (combined_mask * 255).astype(np.uint8)
    data[..., 3] = alpha_channel
    segmented_image = Image.fromarray(data)
    plt.imshow(segmented_image)


def plotimg(image, mask, task=False):
    if task == 'overlay':
        overlay(image, mask)
    else:
        cutout(image, mask)
    plt.axis('off')
    plt.show()



def get_image(image_path):
    return Image.open(image_path).convert('RGB')


if __name__ == '__main__':
    mode = 'infer'
    weigths = 'heads_weights.pt'  # 'yolov8s-seg.pt'
    segmodel = YOLO(weigths)

    if mode == 'train':
        train(segmodel)
    else:
        image = get_image('photo2.png')
        mask = predict(segmodel, image)
        plotimg(image, mask, 'overlay')
