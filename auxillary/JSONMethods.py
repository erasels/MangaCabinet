import json
import logging
import os

from auxillary.DataAccess import MangaEntry

logger = logging.getLogger(__name__)


def load_json(file_path: str, data_type='list'):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                if data_type == "mangas":
                    return json.load(file, object_pairs_hook=MangaEntry)
                else:
                    return json.load(file)
            except json.JSONDecodeError:
                logger.error(f"The file {file_path} contains invalid JSON. Using default {data_type} instead.")
                return [] if data_type == 'list' else {}
    else:
        logger.warning(f"The file {file_path} does not exist. Using default {data_type} instead.")
        return [] if data_type == 'list' else {}


def save_json(file_path: str, input_data):
    with open(file_path, 'w') as file:
        json.dump(input_data, file, indent=4)


def load_styles(style_path):
    styles = {}
    if os.path.exists(style_path):
        for file_name in os.listdir(style_path):
            if file_name.endswith(".qss"):
                with open(os.path.join(style_path, file_name), "r") as f:
                    stylesheet = f.read()
                    # Store the style in the dictionary using the filename without the .qss extension
                    styles[file_name.rsplit('.', 1)[0]] = stylesheet
    return styles
