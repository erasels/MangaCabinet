
class MangaEntry(dict):
    ATTRIBUTE_MAP = {
        "tags": ("tag", []),
        "group": ("MC_Grouping", ""),
        "title": ("title", None),
        "id": ("id", None),
        "author": ("artist", []),
        "language": ("language", []),
        "pages": ("pages", 0),
        "parody": ("parody", []),
        "upload": ("upload_date", None)
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getattr__(self, attr):
        # Using a mapping to get the key and default value
        key, default_value = self.ATTRIBUTE_MAP.get(attr, (None, None))

        # Special handling for "language"
        if attr == "language":
            langs = self.get(key, default_value)
            if "translated" in langs:
                langs.remove("translated")
            return langs
        elif key:
            return self.get(key, default_value)
        elif attr in self:  # If the attr is a direct key in the dictionary
            print(f"Using undefined access to variable for MangaEntry: {attr}")
            return self[attr]
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")

    def display_title(self) -> str:
        return self.get("title_short") or self.get("title_alt") or self.get("title", "")

    def is_translated(self):
        return self.get("language") and "translated" in self["language"]
