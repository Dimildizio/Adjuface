# Project Name

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/Dimildizio/Adjuface?style=social)](https://github.com/Dimildizio/Adjuface/stargazers)

A Telegram bot for generating images with the same face as the input picture using PyTorch Lightning.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Getting Started](#getting-started)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Dependencies](#dependencies)
- [Contributing](#contributing)
- [License](#license)


## Overview

Welcome to the project! This repository hosts a Telegram bot designed to provide an engaging and creative experience for users. The bot's primary functionality revolves around generating images that preserve the facial features of the person in the input image.

Key Features:
- **Telegram Bot Integration**: The Telegram bot is capable of receiving images from users and returning generated images that retain the facial attributes of the input pictures.

- **Modular Architecture**: To ensure maintainability and scalability, the project is structured using a modular architecture. Each module plays a distinct role in the image generation process:
   - **Bot Module**: Manages the integration with the Telegram platform, including endpoints for user interaction.
   - **Segmentation Module**: Focuses on accurately segmenting the facial region within the input image.
   - **Face Extraction Module**: Handles the extraction of the segmented face for further processing.
   - **GANs Module**: Utilizes Generative Adversarial Networks (GANs) to generate images with modified facial features.

- **PyTorch Lightning**: I try to harness the power of PyTorch Lightning to streamline the development and training of machine learning models, enhancing code readability and maintainability.

This project aims to combine the worlds of computer vision, deep learning, and chatbot technologies to create a fun and innovative user experience. Whether you're interested in exploring the codebase, contributing to the project, or just enjoying the results, I hope you find this project both exciting and inspiring.

Feel free to dive into the [Getting Started](#getting-started) section to set up the project and start using the bot! If you have any questions or suggestions, don't hesitate to get in touch. I'm excited to have you as part of the community!


## Features

1. **Telegram Bot Integration**: Users can send a picture of a person to the bot, and the bot will return a generated image with the same face as the original picture.

2. **Modular Architecture**: The project is organized into separate modules to ensure maintainability and scalability:
   - **Bot Module**: Handles Telegram bot integration and endpoints.
   - **Segmentation Module**: Responsible for segmenting the face in the input image.
   - **Face Extraction Module**: Cuts out the segmented face for further processing.
   - **GANs Module**: Utilizes Generative Adversarial Networks for generating images with the modified face.

3. **PyTorch Lightning**: The project leverages PyTorch Lightning to simplify and enhance the training and development process.

## Getting Started

Follow these steps to set up and run the project on your local machine:

### Prerequisites

- Python 3.7+
- PyTorch
- PyTorch Lightning
- Your Telegram API credentials

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/Dimildizio/Adjuface.git

2. Clone the repository:

   ```bash
   pip install -r requirements.txt


3. Configure your Telegram API credentials by creating a config.yaml file and providing the required information.

4. Run the bot:

    ```bash
    python main.py


### Usage

To use the bot, follow these steps:

1. Open Telegram and search for your bot using the username or display name you provided during the bot creation. Default bot is @dimildiziotrybot. It's up and working when it's up and working

2. Start a chat with the bot.

3. Send an image containing a person's face as a message to the bot.

4. TODO: The bot will process the image and return a generated image with the same face as the original picture.

5. ???
   
6. ~~PROFIT!~~ Enjoy experimenting with the bot and exploring its capabilities!


## Project Structure

This project is organized into several modules to ensure modularity and maintainability:

- `/bot`: Contains the Telegram bot code and endpoints.
- `/segmentation`: Handles face segmentation.
- `/face_extraction`: Cuts out the segmented face from images.
- `/gans`: Implements the GANs for image generation.

Each module serves a specific purpose, and the goal is to seamlessly integrate them to create a cohesive user experience. 


### Face Extraction Module

The Face Extraction Module is responsible for isolating the segmented facial region from the input image. It utilizes advanced computer vision techniques to precisely extract the detected face, ensuring that only the relevant portion is retained for further processing. I'm considering two prominent models:

1. **U-Net**: U-Net is a widely used architecture for image segmentation tasks due to its ability to capture fine-grained details while maintaining context. I'm gonna evaluate the use of U-Net for precise facial segmentation. Possibly with focal loss function.

2. **DeepNet v3**: DeepNet v3 represents another state-of-the-art option for segmentation tasks. Its architecture may offer advantages in terms of accuracy and efficiency, and I'm still exploring its potential for the project.

The final selection will depend on various factors, including performance, resource requirements, and ease of integration into the modular architecture. I'm committed to delivering the best results, and the choice of segmentation model will play a significant role in achieving that goal.

### Cutting Tool

The cutting tool within the Face Extraction Module is responsible for precise extraction of the segmented facial region from the input image. Here's an overview of its functionality:

1. **Input Image with Segmented Face**: The cutting tool takes an input image that has undergone facial segmentation, providing a mask or bounding box outlining the location of the segmented face.

2. **Mask or Bounding Box Processing**: Depending on the segmentation method (mask likely), the tool processes the binary mask or bounding box coordinates, identifying the region containing the segmented face.

3. **Image Cropping**: The tool employs image cropping techniques to extract the portion of the input image corresponding to the segmented face. This cropped area contains the facial features of interest.

4. **Optional Preprocessing**: To prepare the face for integration with the GAN model or other downstream tasks, optional preprocessing steps may be applied. These can include resizing, alignment, or other transformations as needed.

5. **Integration with GAN**: After accurate extraction and optional preprocessing, the segmented face is integrated into the latent space of the GAN model. This allows the GAN to generate images with desired facial modifications while retaining the image's overall context.

The cutting tool ensures that the segmented facial region is isolated precisely and maintains its original quality and appearance, facilitating seamless integration with the GAN model. Its implementation accommodates various segmentation outputs and guarantees the generation of high-quality modified images while preserving context.



### GANs (Generative Adversarial Networks)

The project leverages Generative Adversarial Networks (GANs) to generate images with modified facial features. GANs consist of two neural networks, a generator and a discriminator, that compete with each other during training. The generator aims to produce realistic images, while the discriminator's role is to distinguish between real and generated images. This adversarial training process leads to the generation of high-quality images with the desired facial modifications.

The latent space of the GAN model plays a crucial role in this process. It represents a lower-dimensional space where variations in facial features can be controlled and manipulated. The segmented face is inserted into this latent space to generate images with the specified facial attributes, ensuring a seamless blend of the original and modified features.

The integration of these components within the modular architecture enables the creation of a novel and engaging user experience through the Telegram bot.

Which models exactly to use - VAE, CVAE is yet to be determined as well as SOTA architecture and pretrained models.


## Dependencies

The following libraries and frameworks are required to run this project. You can install them using the provided `requirements.txt` file:

- **PyTorch**: `>= 1.6.0`
  - [PyTorch](https://pytorch.org/) for deep learning tasks, including neural networks.

- **PyTorch Lightning**: `>= 1.4.0`
  - [PyTorch Lightning](https://www.pytorchlightning.ai/)  lightweight PyTorch wrapper to simplify training.

- **Hugging Face Transformers**: `>= 4.0.0`
  - [Hugging Face Transformers](https://huggingface.co/transformers/) library for models 

- **aiogram**: `>= 2.15.0`
  - [aiogram](https://docs.aiogram.dev/en/latest/) a framework for building Telegram bots.

- **Pillow**: `>= 8.0.0`
  - [Pillow](https://python-pillow.org/) (PIL) for image processing tasks.

To install these dependencies, you can use the following command:

    ```bash
    pip install -r requirements.txt


## Contributing

I welcome contribution from the community to help make this project even better! Whether you want to report a bug, suggest a feature, or contribute code, here's how you can get involved:

1. **Fork the Repository**: Click the "Fork" button at the top of the repository to create your own copy of the project.

2. **Create a Branch**: Before making any changes, create a new branch for your work. Branch names should be clear and descriptive of the feature or bug you're addressing.

   ```bash
   git checkout -b feature/my-new-feature


3. **Make Changes**: Write your code, fix the bug, or make your improvements. Be sure to follow the coding style and conventions to maintain code consistency.

4. **Test**: Ensure that your changes do not introduce new issues and that all existing tests pass successfully.

5. **Commit**: Commit your changes with a clear and concise commit message following the pattern:

- `feat(segment): Your commit message` for adding new features.
- `fix(segment): Your commit message` for fixing bugs.
- `doc(segment): Your commit message` for documentation updates.
- `refactor(segment): Your commit message` for code refactoring.

 **Example commits**:

- `feat(model): Add U-Net architecture` # For adding a new model.
- `fix(bot): Resolve issue with message handling` # For fixing a bot-related issue.

6. **Push**: Push your branch to your forked repository on GitHub.
    ```bash
    git push origin feat/my-new-feature

7. **Create a Pull Request (PR)**: Go to the original repository on GitHub and create a new Pull Request. Clearly describe the changes you've made and provide any relevant information.

8. **Review and Approval**: I will review your Pull Request. If further changes or improvements are needed, I'll provide feedback and guidance. Once your changes meet the standards, I'll approve the PR.

9. **Merging**: I will merge your approved Pull Request into the main project.

10.  **Thank You!**: Your contribution to the project is greatly appreciated. Thank you for helping make this project better.

Please remember to follow the commit message pattern and contribute to the project following these guidelines. I encourage collaboration and look forward to your contributions!


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


