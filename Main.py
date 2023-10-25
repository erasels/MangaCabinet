import json
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from auxillary.DataAccess import MangaEntry
from auxillary.JSONMethods import load_json, save_json, load_styles
from gui import Options
from gui.Details import DetailViewHandler
from gui.GroupHandler import GroupHandler
from gui.MangaList import MangaDelegate, ListViewHandler
from gui.Options import OptionsHandler
from gui.SearchBarHandler import SearchBarHandler


class MangaApp(QWidget):
    image_path = os.path.join('assets', 'images')
    data_path = os.path.join('assets', 'data')
    style_path = os.path.join('assets', 'styles')

    data_file = os.path.join(data_path, 'data.json')
    settings_file = os.path.join(data_path, 'settings.json')
    groups_file = os.path.join(data_path, 'groups.json')

    def __init__(self):
        super().__init__()
        self.data = load_json(MangaApp.data_file, data_type="mangas")
        # Save entry to its reversed index so that sorting works quickly and as expected
        self.entry_to_index_reversed = {entry.id: len(self.data) - idx - 1 for idx, entry in enumerate(self.data)}
        self.styles = load_styles(MangaApp.style_path)
        self.settings = Options.load_settings(self.settings_file)
        self.init_ui()

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

        self.setLayout(self.layout)

    # Override for updating list when resizing
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.manga_list_handler.handle_resize()


def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Function to capture and display exceptions in a readable manner.
    """
    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    sys.exit(1)


if __name__ == '__main__':
    sys.excepthook = exception_hook  # Set the exception hook to our function

    app = QApplication(sys.argv)
    window = MangaApp()
    window.setWindowTitle("Manga Cabinet")
    window.resize(1280, 720)
    window.show()
    sys.exit(app.exec_())
