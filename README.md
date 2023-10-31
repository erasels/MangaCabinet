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
5. **Upcoming Features**: 
    - Foldering to categorize your manga collection.
    - Enhanced UI for a better user experience.

### Enhanced Search Functionality:
1. **Simple Search**: 
    - Just type in your search term, and it'll look everywhere for you, scanning every nook and cranny of the manga data.
    - Quick Tip: If you're looking to search multiple terms at once, just separate them with a comma!

2. **Field-Specific Search**: 
    - Want to get fancy? You can search within specific fields by using a colon. For example, `tag:Fantasy` would look for Mangas with a Fantasy tag.

3. **Quantity Searches**: 
    - Sometimes, you might be curious about quantities. Like, "How many tags does this manga have?" or "How long is the title?". We got you covered!
    - Use `>` or `<` symbols to find manga entries that match certain conditions. For instance:
      - `tag:>30` - Finds manga with more than 30 tags.
      - `title:<10` - Fetches manga with titles less than 10 characters long.
      - `pages:>100` - Returns manga with more than 100 pages.

4. **And More**: 
    - You can also narrow down your searches within specific groups.
    - Sort the results by upload date, score, id or data order
    - Enable loose matching so only one of your search terms needs to be a hit for the result to show

