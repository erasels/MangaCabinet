import json
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QColor
from PyQt5.QtWidgets import *

from auxillary.BrowserHandling import BrowserHandler
from auxillary.DataAccess import MangaEntry, TagData
from auxillary.JSONMethods import load_json, load_styles, save_json
from auxillary.Thumbnails import ThumbnailManager
from gui import Options
from gui.DetailEditor import DetailEditorHandler
from gui.DetailView import DetailViewHandler
from gui.GroupHandler import GroupHandler
from gui.MangaList import ListViewHandler
from gui.Options import OptionsHandler
from gui.SearchBarHandler import SearchBarHandler
from gui.TagViewer import TagViewer
from gui.WidgetDerivatives import ToastNotification

log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file_path = os.path.join(log_dir, 'log.txt')
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
                    datefmt='%y/%m/%d %H:%M:%S',
                    handlers=[RotatingFileHandler(log_file_path, maxBytes=5 * 1024 * 1024, backupCount=2),
                              logging.StreamHandler(sys.stdout)])


class MangaCabinet(QWidget):
    config_path = os.path.join('assets', 'data')

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.toast = None
        self.setWindowTitle("Manga Cabinet")
        self.resize(1280, 720)
        self.fonts = ["Tahoma", "Arial", "Verdana"]
        self.font_index = 0
        self.is_data_modified = False
        self.load_config_values()
        self.data = load_json(self.data_file, data_type="mangas")
        self.common_attributes = sorted(
            set(MangaEntry.ATTRIBUTE_MAP) | set(MangaEntry.FIELD_ALIASES_AND_GROUPING),
            key=str.lower
        )
        self.entry_to_index = {}
        self.tag_data = TagData()
        self.all_artists = set()
        self.all_ids = []
        self.init_infos()
        self.details_view = None
        self.tag_view = None
        self.styles = load_styles(self.style_path)
        self.settings = Options.load_settings(self.settings_file)
        self.thumbnail_manager = ThumbnailManager(self.data, self.download_thumbnails, self.tags_to_blur)
        self.thumbnail_manager.startEnsuring.emit()
        self.browser_handler = BrowserHandler(self)
        self.init_ui()
        self.show()
        self.logger.info(f"Successfully initialized with {len(self.data)} entires.")

    def load_config_values(self):
        config_file = os.path.join(MangaCabinet.config_path, "config.json")
        default_config_file = os.path.join(MangaCabinet.config_path, "config_default.json")
        config_file = config_file if os.path.exists(config_file) else default_config_file
        with open(config_file, 'r') as f:
            config = json.load(f)
            self.logger.debug(f"Loaded config: {config_file}\n{config}")
            self.data_file = config["data_file"]
            self.settings_file = config["settings_file"]
            self.groups_file = config["groups_file"]
            self.style_path = config["style_path"]
            self.image_path = config["image_path"]
            self.browser_path = config["browser_executable_path"]
            self.browser_flags = config["browser_flags"]
            self.default_URL = config["default_url"]
            self.download_thumbnails = config["download_thumbnails"]
            self.tags_to_blur = config.get("tags_to_blur", [])

    def init_ui(self):
        self.changeFont()
        self.layout = QVBoxLayout()

        # Init options button and add logic for it
        self.options_handler = OptionsHandler(self)
        # Handles entire search bar and accesses settings_buton
        self.search_bar_handler = SearchBarHandler(self)
        # Handles entire groups bar
        self.group_handler = GroupHandler(self)
        # Handles looking at and modifying details of manga entries
        self.details_handler = DetailEditorHandler(self)
        self.options_handler.bindViewChanged.connect(lambda state: self.details_handler.image_view.set_dynamic_show(state))
        # Handles the manga list view
        self.manga_list_handler = ListViewHandler(self)
        # Setup initial list once components are in place
        self.search_bar_handler.update_list(False)

        # Setup layout (wdiget = single item, layout = group of items)
        self.layout.addLayout(self.search_bar_handler.get_layout(self.group_handler.get_widgets() + [self.options_handler.get_widget()]))

        self.vertical_layout = QVBoxLayout()
        list_widget = self.manga_list_handler.get_widget()
        list_widget.setMinimumHeight(335)
        self.vertical_layout.addWidget(list_widget, 1)
        self.vertical_layout.addLayout(self.details_handler.get_layout(), 0)

        self.layout.addLayout(self.vertical_layout)

        self.setLayout(self.layout)
        self.toast = ToastNotification(self)

    # Override for updating list when resizing
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.manga_list_handler.handle_resize()
        self.details_handler.handle_resize()

    def closeEvent(self, event):
        if self.details_view:
            self.details_view.close()
        if self.tag_view:
            self.tag_view.close()
        super(MangaCabinet, self).closeEvent(event)

    def save_changes(self):
        if self.is_data_modified:
            save_json(self.data_file, self.data)
            self.logger.info("Saved data.")
        self.logger.info("Terminated.")

    def open_detail_view(self, entry):
        if self.details_view:
            self.details_view.update_data(entry)
        else:
            self.details_view = DetailViewHandler(self, entry)

    def open_tag_view(self):
        if not self.tag_view:
            self.tag_view = TagViewer(self)

        self.tag_view.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F2:
            self.font_index = (self.font_index + 1) % len(self.fonts)
        elif event.key() == Qt.Key_F1:
            self.font_index = (self.font_index - 1) % len(self.fonts)
        else:
            super().keyPressEvent(event)
            return

        self.changeFont()

    def changeFont(self):
        prev_name = self.font().family()
        font = QFont(self.fonts[self.font_index], 9)
        self.setFont(font)
        self.logger.info(f"Changing font from {prev_name} to {self.fonts[self.font_index]}")

    def init_infos(self):
        for idx, entry in enumerate(self.data):
            self.entry_to_index[entry.id] = idx
            self.all_artists.update(entry.artist)
            self.all_ids.append(entry.id)
            self.tag_data.update_with_entry(entry)


def exception_hook(exc_type, exc_value, exc_traceback):
    """
    Function to capture and display exceptions in a readable manner and saves data to prevent loss.
    """
    try:
        window.save_changes()
    except Exception as e:
        # Log the error or print it out. This is to ensure that if the save fails,
        # it doesn't prevent the original exception from being displayed.
        logger = logging.getLogger(__name__)
        logger.critical(f"Error during save: {e}")

    sys.__excepthook__(exc_type, exc_value, exc_traceback)
    sys.exit(1)


if __name__ == '__main__':
    sys.excepthook = exception_hook  # Set the exception hook to our function
    logging.getLogger('PIL').setLevel(logging.WARNING)

    app = QApplication(sys.argv)
    # Custom dark palette from https://stackoverflow.com/questions/48256772/dark-theme-for-qt-widgets
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, QColor(225, 225, 225))
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.Text, QColor(225, 225, 225))
    palette.setColor(QPalette.ButtonText, QColor(225, 225, 225))
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(75, 35, 194))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)
    window = MangaCabinet()
    app.aboutToQuit.connect(window.save_changes)
    sys.exit(app.exec_())
