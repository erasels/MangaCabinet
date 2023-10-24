import os
import sys
import json

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QSize

from auxillary.JSONMethods import load_json, save_json, load_styles
from gui.ComboBoxDerivatives import RightClickableComboBox
from gui.GroupHandler import GroupHandler
from gui.MangaList import MangaDelegate
from gui.SearchBarHandler import SearchBarHandler
from gui.Options import OptionsDialog, init_settings, search_thrshold
from auxillary.DataAccess import MangaEntry


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
        self.settings = None
        self.load_settings()
        self.init_ui()

    def load_settings(self):
        settings = load_json(MangaApp.settings_file, "dict")
        if settings:
            self.settings = settings
        else:
            init_settings()

    # Method to create settings window
    def show_options_dialog(self):
        self.dialog = OptionsDialog(parent=self)
        if self.dialog.exec_() == 0:
            self.search_bar_handler.update_list()
            save_json(MangaApp.settings_file, self.settings)

    def init_ui(self):
        self.layout = QVBoxLayout()

        # Search bar
        self.search_bar = QLineEdit(self)
        # Hits label
        self.hits_label = QLabel(self)
        self.hits_label.hide()
        # Sort drop down
        self.sort_combobox = RightClickableComboBox()

        self.search_bar_handler = SearchBarHandler(self)

        # Options Button
        self.settings_button = QPushButton(self)
        self.settings_button.setIcon(QIcon(os.path.join(MangaApp.image_path, 'options_icon.png')))
        self.settings_button.setIconSize(QSize(24, 24))
        self.settings_button.setFixedSize(24, 24)  # Set the button size to match the icon size
        self.settings_button.setStyleSheet("QPushButton { border: none; }")  # Remove button styling
        self.settings_button.clicked.connect(self.show_options_dialog)

        search_box = QHBoxLayout()  # Create a horizontal box layout
        search_box.addWidget(self.search_bar, 1)  # The '1' makes the search bar expand to fill available space
        search_box.addWidget(self.hits_label)
        search_box.addWidget(self.sort_combobox)
        search_box.addWidget(self.settings_button)
        self.layout.addLayout(search_box)

        self.group_handler = GroupHandler(self)

        # List view
        self.list_view = QListView(self)
        self.list_model = QStandardItemModel(self.list_view)
        self.list_view.setModel(self.list_model)

        self.list_view.setWrapping(True)
        self.list_view.setFlow(QListView.LeftToRight)
        self.list_view.setLayoutMode(QListView.Batched)

        self.list_delegate = MangaDelegate(self, self.list_view)
        self.list_view.setItemDelegate(self.list_delegate)
        self.list_view.clicked.connect(self.display_detail)
        self.layout.addWidget(self.list_view)
        self.search_bar_handler.update_list(False)

        # Detail view (as a text edit for simplicity)
        self.detail_view = QTextEdit(self)
        self.layout.addWidget(self.detail_view)

        # Save button
        self.save_button = QPushButton("Save Changes", self)
        self.save_button.clicked.connect(self.save_changes)
        self.save_button.setStyleSheet(self.styles.get("textbutton"))
        self.layout.addWidget(self.save_button)

        self.setLayout(self.layout)

    # Override for updating list when resizing
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.list_view.updateGeometries()
        self.list_view.doItemsLayout()  # Force the view to relayout items.

    def display_detail(self, index):
        data = index.data(Qt.UserRole)
        self.detail_view.setText(json.dumps(data, indent=4))

    def save_changes(self):
        contents = self.detail_view.toPlainText()
        if len(contents) > 5:
            current_data = json.loads(contents, object_pairs_hook=MangaEntry)
            for i, entry in enumerate(self.data):
                if entry.id == current_data['id']:
                    self.data[i] = current_data
                    save_json(MangaApp.data_file, self.data)
                    self.search_bar_handler.update_list()
                    break


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
