import cv2
import os
import numpy as np
from tqdm import tqdm


def get_address(txt):
    return f'CelebAMask-HQ/YOLOFormat/{txt}/train'


def resize_and_center_image(image, size=(512, 512), is_mask=False):
    """Resize and center the image or mask in a 640x640 frame."""
    h, w = image.shape[:2]
    scale = min(size[0] / h, size[1] / w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    resized = cv2.resize(image, (new_w, new_h))

    if is_mask:
        return resized
        #  canvas = np.zeros((size[0], size[1]), dtype=np.uint8)  # Black canvas for mask
    #  else:
    canvas = np.zeros((size[0], size[1], 3), dtype=np.uint8)  # Black canvas for image
    # Center the image or mask in the canvas
    x_offset = (size[1] - new_w) // 2
    y_offset = (size[0] - new_h) // 2
    canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized
    return canvas


def overlay_mask(image, mask, alpha=0.3):
    """Overlay mask onto image with specified transparency."""
    mask_indices = cv2.resize(mask, (image.shape[1], image.shape[0])) > 0  # Where mask is white
    overlay = image.copy()
    overlay[mask_indices] = (1 - alpha) * image[mask_indices] + alpha * np.array([200, 200, 0])
    return overlay


def load_images_and_masks(images_dir, masks_dir, max_images=100):
    """Load images and corresponding masks."""
    imgs, msks = [], []
    image_files = sorted([f for f in os.listdir(images_dir) if f.endswith(('.jpg', '.png'))])[:max_images]

    for img_name in tqdm(image_files, desc="Loading images"):
        img_path = os.path.join(images_dir, img_name)
        mask_path = os.path.join(masks_dir, img_name.replace('.jpg', '.png'))

        if os.path.exists(mask_path):
            img = cv2.imread(img_path)
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

            if img is not None and mask is not None:
                imgs.append(img)
                msks.append(mask)
            else:
                print(f"Failed to load image or mask for {img_name}")
        else:
            print(f"No mask found for image {img_name}")
    return imgs, msks


images, masks = load_images_and_masks(get_address('images'), get_address('labels'), 100)
index = 0

while True:
    resized_image = resize_and_center_image(images[index])
    resized_mask = resize_and_center_image(masks[index], is_mask=True)
    combined = overlay_mask(resized_image, resized_mask)
    cv2.imshow('Image with Mask', combined)

    key = cv2.waitKeyEx(0)
    if key == 2555904 and index < len(images) - 1:  # Right arrow for windows
        index += 1
    elif key == 2424832 and index > 0:  # Left arrows for windows
        index -= 1
    elif key == 27 or key == ord('q'):  # Escape
        break

cv2.destroyAllWindows()
