import os
from datetime import datetime, timedelta
from typing import Tuple


def list_project_structure(path: str, to_ignore: Tuple[str, ...], indent: int = 0) -> None:
    """
    Lists the project directory structure, ignoring specified directories.

    :param path: The path to the directory to list.
    :param to_ignore: A list of directory names to ignore.
    :param indent: The indentation level for printing the directory structure.
    """
    if os.path.isdir(path):
        folder_name = os.path.basename(path)
        if folder_name not in to_ignore and not folder_name.startswith('.'):
            print(' ' * indent + '-' + folder_name)
            for item in os.listdir(path):
                new_path = os.path.join(path, item)
                list_project_structure(new_path, to_ignore, indent + 4)
    else:
        file_name = os.path.basename(path)
        if not file_name.startswith('.'):
            print(' ' * indent + '-' + file_name)


async def remove_old_image(paths=('temp\\result', 'temp\\original', 'temp\\target_images'),
                           hour_delay: int = 48, name_start: str = 'img'):
    """
    Removes images that are older than a specified time delay and start with a specified name from a folders.

    :param paths: The names of the folders to parse.
    :param hour_delay: The age threshold in hours for deleting an image.
    :param name_start: The prefix of the image filenames to consider for deletion.
    :return: None
    """
    now = datetime.now()
    time_threshold = timedelta(hours=hour_delay)
    for folder_path in paths:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(os.getcwd(), folder_path, filename)

            if filename.startswith(name_start) and os.path.isfile(file_path):
                file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                if now - file_creation_time > time_threshold:
                    os.remove(file_path)
                    print(f"Deleted: {file_path} - {file_creation_time}")


if __name__ == "__main__":
    remove_old_image(hour_delay=24)

    ignore = ('temp', '__pycache__', 'research')
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # os.getcwd()
    list_project_structure(project_root, ignore)
