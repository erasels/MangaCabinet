import json
import uuid
from datetime import datetime

data = {
    "id": str(uuid.uuid4()),
    "description": "",
    "title": "To be edited",
    "title_short": "",
    "tag": [],
    "artist": [],
    "group": [],
    "language": [],
    "pages": 0,
    "parody": [],
    "character": [],
    "upload": datetime.now().strftime("%Y/%m/%d %H:%M"),
    "score": 0,
    "similar": []
}

# Printing the json.dumps data is how the value is transferred to the main window, this can also pass a list of dicts
print(json.dumps(data))
