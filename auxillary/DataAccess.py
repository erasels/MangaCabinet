import logging
from datetime import datetime


class MangaEntry(dict):
    ATTRIBUTE_MAP = {
        "id": ("id", None),
        "description": ("description", ""),
        "title": ("title", ""),
        "title_short": ("title_short", ""),
        "tags": ("tag", []),
        "artist": ("artist", []),
        "artist_group": ("group", []),
        "language": ("language", []),
        "pages": ("pages", 0),
        "parody": ("parody", []),
        "upload": ("upload_date", None),
        "score": ("score", 0),
        "group": ("MC_Grouping", None),
        "similar": ("similar", []),
        "open_url": ("open_url", ""),
        "thumbnail_url": ("thumbnail_url", "")
    }

    # Could be moved into a json file, but fits for now
    FIELD_ALIASES_AND_GROUPING = {
        "tags": ["tag"],
        "artist": ["artist", "group"],
        "author": ["artist", "group"],
        "upload": ["upload_date"],
        "title": ["title", "title_alt", "title_short"],
        "rating": ["score"]
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)

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
        return self.get("title_short") or self.get("title_alt") or self.get("title", "")

    def first_artist(self):
        artists = self.get("artist", [])
        if not artists:
            group = self.get("group", [])
            if group:
                return group[0]
        else:
            return artists[0]
        return ""

    def is_translated(self):
        return self.get("language") and "translated" in self["language"]

    def upload_date(self):
        if self.upload:
            return datetime.strptime(self.upload, "%Y/%m/%d %H:%M")
        else:
            return None
