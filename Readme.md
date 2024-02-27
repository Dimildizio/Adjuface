# Adjuface - Telegram Face Swapping Bot

![Adjuface Logo](https://github.com/Dimildizio/Adjuface/assets/42382713/4880c3ac-296f-4612-a249-8eef73d69921)

Adjuface is a Telegram bot that allows users to swap faces in images. With Adjuface, you can easily create humorous and creative images by swapping faces in photos. The bot is equipped with various features and capabilities to provide an enjoyable face-swapping experience.



https://github.com/Dimildizio/Adjuface/assets/42382713/8f2a0a6b-dd97-4593-a97d-520b72fa4db0


For better quality click the [link](https://www.youtube.com/watch?v=01Qah4aU_rE)


## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
    
- [Usage](#usage)
  - [Commands](#commands)
  - [Face Swapping](#face-swapping)
  - [Bot usecase](#Usecase)   

- [Examples](#examples)
- [Work In Progress](#work-in-progress)
- [Contributing](#contributing)
- [License](#license)

## Getting Started

### Prerequisites

To run Adjuface locally or on your own server, you will need the following:

- Python 3.7+
- Microsoft Visual C++ 14 Build tools 
- Telegram bot token
- ONNX model file (train your own or follow [this](https://github.com/deepinsight/insightface/tree/master/examples/in_swapper) insightface guidline to get)

### Installation

1. Clone the repository:

   ```shell
   git clone https://github.com/Dimidizio/Adjuface.git

2. Install dependencies:

  ```shell
  pip install -r requirements.txt
  ```

3. Set up your bot token:
  Create a bot on Telegram and obtain your API token.


4. Create a **config.yaml** file in the project directory and add your token:
  ```shell
  token: YOUR_BOT_TOKEN
  ```
5. Create a target_images.json file with your categories for your target images and address as well as collages for your categories:
```shell
{
  "categories": {
    "art": [
      {
        "mode": "1",
        "name": "Peter the Great",
        "filepath": PATH_TO_THE_IMAGE
      },
    ]
}
"collages": {
    "art": PATH_TO_THE_COLLAGE,

  }
}
```

6. Create a **contacts.yaml** file in the project /bot directory and add your token:
  ```shell
  telegram: YOUR_TG_ACCOUNT
  github: github.com/Dimildizio
  my_id: 12345678
  cryptohash: bc1j7f93nc7s4nc74n32sc43nu3tc
  botname: YOUR_BOT_NAME
token: YOUR_BOT_TOKEN
```

7. Go to the /face_carver folder, put your onnx file there (default is inswapper_128.oonx) and run Fast API
   ```shell
   cd face_carver
   uvicorn swapper:app --reload


8. Run main.py to start the bot

**Commands**

Adjuface supports various commands that users can send in their Telegram chats to interact with the bot. Here are some common commands:

- `/start`: Start the bot.
- `/help`: Display help and available commands.
- `/status`: Check your account limits.
- `/menu`: Select a category of pictures for face swapping.
- `/buy_premium`: Add 100 images and set your account to premium.
- `/target`: Premium option to add your custom target image.
- `/contacts`: Show the bot owner's contacts from contacts.yaml
- `/support`: Send a support request to the bot owner.
- `/donate`: Support the bot owner.

**Face Swapping**

To swap faces in an image, simply send a photo to the bot. If the image contains faces, the bot will process it and return the swapped image(s). If you have custom target images, you can specify which face to swap with.

**Usecase**

Here is an instruction to use [@Adjuface_bot](https://t.me/Adjuface_bot) TG bot

![image](https://github.com/Dimildizio/Adjuface/assets/42382713/dcfd91f0-537d-4216-bb96-cdf5c38508d5)


**Examples**

Here are some examples of face swapping using Adjuface:


![image](https://github.com/Dimildizio/Adjuface/assets/42382713/578dcd4f-f23b-4481-87ed-2d20222240ea)

**Work In Progress**



https://github.com/Dimildizio/Adjuface/assets/42382713/17697432-3a01-44ec-936e-97a86412ec53



**Contributing**

Contributions to Adjuface are welcome! If you have ideas for improvements, bug reports, or feature requests, please open an issue or submit a pull request. We appreciate your help in making Adjuface even better.

**License**

This project is licensed under the MIT License.
