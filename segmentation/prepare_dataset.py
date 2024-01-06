import os
import shutil
import random
import yaml
import cv2


# Define paths
dataset_path = 'CelebAMask-HQ'
mask_path = os.path.join(dataset_path, 'CelebAMask-HQ-mask-anno')
image_path = os.path.join(dataset_path, 'CelebA-HQ-img')  # Path to the CelebA-HQ images
output_path = os.path.join(dataset_path, 'YOLOFormat')
image_counter = 0


def resize_image(image_path, output_size=(512, 512)):
    """Resize an image to the given size."""
    image = cv2.imread(image_path)
    return cv2.resize(image, output_size)


os.makedirs(output_path, exist_ok=True)
for i in ('images', 'labels'):
    for j in ('train', 'val', 'test'):
        os.makedirs(os.path.join(output_path, i, j), exist_ok=True)


for folder_index in range(15):  # CelebFaceHQ got 15 folders (0-14)
    folder_path = os.path.join(mask_path, str(folder_index))

    for filename in os.listdir(folder_path):
        if filename.endswith('_skin.png') and filename != '.DS_Store':
            # Process only every 5th image
            if image_counter % 5 != 0:
                image_counter += 1
                continue
            if image_counter % 500 == 0:
                print(image_counter)
            # Determine split (train/val/test)
            split = random.choices(['train', 'val', 'test'], [0.7, 0.15, 0.15])[0]

            # Copy the skin mask file to the corresponding directory
            file_path = os.path.join(folder_path, filename)
            output_mask_path = os.path.join(output_path, 'labels', split, f'{image_counter}.png')
            shutil.copy(file_path, output_mask_path)

            # Copy the corresponding image
            image_file_name = f'{image_counter}.jpg'  # Image files named like '1.jpg', '2.jpg', etc.
            image_file_path = os.path.join(image_path, image_file_name)
            #  output_image_path = os.path.join(output_path, 'images', split, image_file_name)
            if os.path.exists(image_file_path):  # Check if the image file exists
                #  shutil.copy(image_file_path, output_image_path)
                resized_image = resize_image(image_file_path)
                output_image_path = os.path.join(output_path, 'images', split, image_file_name)
                cv2.imwrite(output_image_path, resized_image)
            image_counter += 1

# Create YAML file for dataset configuration
yaml_content = {
    'train': os.path.join(output_path, 'images', 'train'),
    'val': os.path.join(output_path, 'images', 'val'),
    'test': os.path.join(output_path, 'images', 'test'),
    'nc': 1,
    'names': ['face']
}

with open(os.path.join(output_path, 'dataset.yaml'), 'w') as yaml_file:
    yaml.dump(yaml_content, yaml_file)

print("Dataset processing, trimming, and splitting complete.")
