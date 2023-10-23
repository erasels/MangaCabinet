import json
import os

from auxillary.DataAccess import MangaEntry


def load_json(file_path: str, data_type='list'):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                if data_type == "mangas":
                    return json.load(file, object_pairs_hook=MangaEntry)
                else:
                    return json.load(file)
            except json.JSONDecodeError:
                print(f"Warning: The file {file_path} contains invalid JSON. Using default {data_type} instead.")
                return [] if data_type == 'list' else {}
    else:
        print(f"Warning: The file {file_path} does not exist. Using default {data_type} instead.")
        return [] if data_type == 'list' else {}


def save_json(file_path: str, input_data):
    with open(file_path, 'w') as file:
        json.dump(input_data, file, indent=4)
