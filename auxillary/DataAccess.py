import logging
from datetime import datetime


class MangaEntry(dict):
    logger = logging.getLogger(__name__)

    ATTRIBUTE_MAP = {
        "id": ("id", None),
        "description": ("description", ""),
        "title": ("title", ""),
        "title_alt": ("title_alt", ""),
        "title_short": ("title_short", ""),
        "tags": ("tag", []),
        "artist": ("artist", []),
        "group": ("group", []),
        "language": ("language", []),
        "pages": ("pages", 0),
        "parody": ("parody", []),
        "character": ("character", []),
        "upload": ("upload_date", None),
        "score": ("score", 0),
        "collection": ("MC_Collection", None),
        "similar": ("similar", []),
        "open_url": ("open_url", ""),
        "thumbnail_url": ("thumbnail_url", ""),
        "opens": ("MC_num_opens", 0),
        "last_opened": ("MC_last_open", None),
        "last_edited": ("MC_last_edited", None),
        "removed": ("removed", False)
    }

    # Could be moved into a json file, but fits for now
    # Takes precedence over attribute map for searching
    FIELD_ALIASES_AND_GROUPING = {
        "tags": ["tag"],
        "artist": ["artist", "group"],
        "author": ["artist", "group"],
        "upload": ["upload_date"],
        "title": ["title", "title_alt", "title_short"],
        "rating": ["score"],
        "stars": ["score"],
        "deprecated": ["removed"],
        "col": ["collection"]
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getattr__(self, attr):
        # Using a mapping to get the key and default value
        key, default_value = self.ATTRIBUTE_MAP.get(attr, (None, None))

        # Special handling for "language"
        if key:
            return self.get(key, default_value)
        elif attr in self:  # If the attr is a direct key in the dictionary
            self.logger.warning(f"Using undefined access to variable for MangaEntry: {attr}")
            return self[attr]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")

    def __setattr__(self, attr, value):
        # Check if the attribute is in the mapping
        key, _ = self.ATTRIBUTE_MAP.get(attr, (None, None))
        if key:
            # If the attribute corresponds to a dictionary key, set it
            self[key] = value
        else:
            # If not, set it as a regular attribute
            super().__setattr__(attr, value)

    def __delattr__(self, attr):
        key, _ = self.ATTRIBUTE_MAP.get(attr, (None, None))
        if key and key in self:
            del self[key]
        else:
            super().__delattr__(attr)

    def display_title(self) -> str:
        return self.title_short or self.title_alt or self.title

    def first_artist(self):
        artists = self.artist
        if not artists:
            group = self.group
            if group:
                return group[0]
        else:
            return artists[0]
        return ""

    def is_translated(self):
        return self.language and "translated" in self.language

    def good_story(self):
        return "good story" in self.tags

    def good_art(self):
        return "good art" in self.tags

    def upload_date(self):
        if self.upload:
            return datetime.strptime(self.upload, "%Y/%m/%d %H:%M")
        else:
            return None

    def edit_date(self):
        if self.last_edited:
            return datetime.strptime(self.last_edited, "%Y/%m/%d %H:%M")
        else:
            return None

    def update_last_edited(self):
        self.last_edited = datetime.now().strftime("%Y/%m/%d %H:%M")
        self.logger.debug(f"{self.id}: MC_last_edited was updated with: {self.last_edited}")

    def update_last_opened(self):
        self.last_opened = datetime.now().strftime("%Y/%m/%d %H:%M")
        self.logger.debug(f"{self.id}: MC_last_opened was updated with: {self.last_opened}")


class TagData(dict):
    def sorted_keys(self):
        return sorted(self.keys(), key=str.lower)

    def update_with_entry(self, entry):
        for tag in entry.tags:
            if tag not in self:
                self[tag] = {'count': 0, 'ids': []}
            self[tag]['count'] += 1
            self[tag]['ids'].append(entry.id)

    def remove_entry(self, entry):
        id = entry.id
        for tag in entry.tags:
            if tag in self and id in self[tag]['ids']:
                self[tag]['ids'].remove(id)
                self[tag]['count'] -= 1
