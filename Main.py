import json
import os
import sys

from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import *

from auxillary.JSONMethods import load_json, load_styles, save_json
from gui import Options
from gui.Details import DetailViewHandler
from gui.GroupHandler import GroupHandler
from gui.MangaList import ListViewHandler
from gui.Options import OptionsHandler
from gui.SearchBarHandler import SearchBarHandler


class MangaApp(QWidget):
    config_path = os.path.join('assets', 'data')

    def __init__(self):
        super().__init__()
        self.is_data_modified = False
        self.load_paths()
        self.data = load_json(self.data_file, data_type="mangas")
        self.entry_to_index = {}
        self.all_tags = set()
        self.all_ids = []
        for idx, entry in enumerate(self.data):
            # Save entry to its reversed index so that sorting works quickly and as expected
            self.entry_to_index[entry.id] = idx
            self.all_tags.update(entry.tags)
            self.all_ids.append(str(entry.id))
        self.all_tags = sorted(self.all_tags, key=str.lower)
        self.styles = load_styles(self.style_path)
        self.settings = Options.load_settings(self.settings_file)
        self.init_ui()

    def load_paths(self):
        config_file = os.path.join(MangaApp.config_path, "config.json")
        default_config_file = os.path.join(MangaApp.config_path, "config_default.json")
        config_file = config_file if os.path.exists(config_file) else default_config_file
        with open(config_file, 'r') as f:
            config = json.load(f)
            self.data_file = config["data_file"]
            self.settings_file = config["settings_file"]
            self.groups_file = config["groups_file"]
            self.style_path = config["style_path"]
            self.image_path = config["image_path"]

    def init_ui(self):
        self.layout = QVBoxLayout()

        # Init options button and add logic for it
        self.options_handler = OptionsHandler(self)
        # Handles entire search bar and accesses settings_buton
        self.search_bar_handler = SearchBarHandler(self)
        # Handles looking at and modifying details of manga entries
        self.details_handler = DetailViewHandler(self)
        # Handles entire groups bar
        self.group_handler = GroupHandler(self)
        # Handles the manga list view
        self.manga_list_handler = ListViewHandler(self)
        # Setup initial list once components are in place
        self.search_bar_handler.update_list(False)

        # Setup layout (wdiget = single item, layout = group of items)
        self.layout.addLayout(self.search_bar_handler.get_layout(self.options_handler.get_widget()))
        self.layout.addLayout(self.group_handler.get_layout())
        self.layout.addWidget(self.manga_list_handler.get_widget())
        for widget in self.details_handler.get_widgets():
           self.layout.addWidget(widget)
        self.layout.addLayout(self.details_handler.get_layout())

        self.setLayout(self.layout)

    # Override for updating list when resizing
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.manga_list_handler.handle_resize()

    def save_changes(self):
        if self.is_data_modified:
            save_json(self.data_file, self.data)
            print("Saved data.")


def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Function to capture and display exceptions in a readable manner and saves data to prevent loss.
    """
    try:
        window.save_changes()
    except Exception as e:
        # Log the error or print it out. This is to ensure that if the save fails,
        # it doesn't prevent the original exception from being displayed.
        print(f"Error during save: {e}")

    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    sys.exit(1)


if __name__ == '__main__':
    sys.excepthook = exception_hook  # Set the exception hook to our function

    app = QApplication(sys.argv)
    window = MangaApp()
    window.setWindowTitle("Manga Cabinet")
    window.resize(1280, 720)
    window.show()
    app.aboutToQuit.connect(window.save_changes)
    sys.exit(app.exec_())
