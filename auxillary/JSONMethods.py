import datetime
import json
import logging
import os
import shutil
import tempfile

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
            except json.JSONDecodeError as ex:
                if data_type == "mangas":
                    raise Exception("The data file had invalid json, fix this!", f"location: {file_path}\nError: {ex}")
                logger.error(f"The file {file_path} contains invalid JSON. Using default {data_type} instead.")
                return [] if data_type == 'list' else {}
    else:
        logger.warning(f"The file {file_path} does not exist. Using default {data_type} instead.")
        return [] if data_type == 'list' else {}


def save_json(file_path: str, input_data):
    logger.debug(f"Saving file as json: {file_path}")
    # Create a temporary file
    temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(file_path))
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
            json.dump(input_data, temp_file, indent=4)
        # If the file was written successfully, try to replace the original file
        try:
            os.replace(temp_path, file_path)
        except OSError as e:
            logger.error(f"Error replacing the original file with the new file: {e}")
            new_file_name = os.path.basename(file_path)
            backup_name = f"{new_file_name}.backup_{datetime.datetime.now():%Y%m%d%H%M%S}"
            backup_path = os.path.join(os.path.dirname(file_path), backup_name)
            shutil.move(temp_path, backup_path)
            logger.warning(f"Moved temporary file to backup at {backup_path}. Please check manually.")
    except Exception as ex:
        logger.error(f"Failed to save JSON data: {ex}\nWriting corrupted data into recovery file and keeping old save.")
        with open(f"{file_path}.recovery", 'w', encoding='utf-8', errors='replace') as recovery_file:
            recovery_file.write(str(input_data))
        # Clean up the temporary file if it still exists
        if os.path.exists(temp_path):
            os.remove(temp_path)


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
