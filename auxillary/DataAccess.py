
class MangaEntry(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __getattr__(self, attr):
        if attr == "tags":
            return self.get("tag", [])
        elif attr == "group":
            return self.get('MC_Grouping', "")
        elif attr == "title":
            return self.get('title')
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")

    def display_title(self) -> str:
        return self.get("title_short") or self.get("title_alt") or self.get("title", "")
