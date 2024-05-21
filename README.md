## Manga Cabinet

Manga Cabinet is a lightweight local application designed to help manga enthusiasts and collectors maintain an organized and searchable collection of manga metadata. With a simple yet efficient UI, this application lets you manage your manga details in one place. The data is ingested from a JSON file, allowing you to view, search, and edit the metadata conveniently.

While using 3rd-party packages has been avoided where possible to keep setup simple and quick, some are still required:
- PyQt5
- requests
- aiohttp
- Pillow

### Features

1. **List & Detailed View**: Easily browse through a list of all manga entries. Click on any entry to open a detailed view.
2. **Search Functionality**: 
    - Search through metadata like titles, tags, authors, and more.
3. **Edit & Save**: Modify the metadata in the detailed view and save your changes back to the original JSON file.
4. **Completely Local**: No internet? No problem. Everything runs locally, ensuring your data remains private.

### Enhanced Search Functionality:
1. **Simple Search**: 
    - Just type in your search term, and it'll look everywhere for you, scanning every nook and cranny of the manga data.
    - Quick Tip: If you're looking to search multiple terms at once, just separate them with a comma!

2. **Field-Specific Search**: 
    - Want to get fancy? You can search within specific fields by using a colon. For example, `tags:Fantasy` would look for Mangas with a Fantasy tag.

3. **Quantity Searches**: 
    - Sometimes, you might be curious about quantities. Like, "What manages have more than X tags?" or "How many titles are longer than X characters?". We got you covered!
    - Use `>`, `<` or `=` symbols to find manga entries that match certain conditions. For instance:
      - `tag:>30` - Finds manga with more than 30 tags.
      - `title:<10` - Fetches manga with titles less than 10 characters long.
      - `pages:=100` - Returns manga with exactly 100 pages.

4. **And More**: 
    - It's possible to negate a search term by prefixing it with a `-` (e.g. `-cute` or `-tag:horror`)
    - You can also narrow down your searches within specific collections.
    - Sort the results by upload date, score, id, data order and more
    - Use a semicolon (`;`) to perform multiple separate searches in one query (e.g. `yandere, gore; horror, tags:romance`).
