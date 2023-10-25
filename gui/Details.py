import json

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTextEdit, QPushButton

from auxillary.DataAccess import MangaEntry
from auxillary.JSONMethods import save_json


class DetailViewHandler:
    def __init__(self, parent):
        self.save_button = None
        self.detail_view = None
        self.mw = parent

        self.init_ui()

    def init_ui(self):
        # Detail view
        self.detail_view = QTextEdit(self.mw)
        self.detail_view.setPlaceholderText("Select an item to edit it.")

        # Save button
        self.save_button = QPushButton("Save Changes", self.mw)
        self.save_button.clicked.connect(self.save_changes)
        self.save_button.setStyleSheet(self.mw.styles.get("textbutton"))

    def get_widgets(self):
        return self.detail_view, self.save_button

    def display_detail(self, index):
        data = index.data(Qt.UserRole)
        self.detail_view.setText(json.dumps(data, indent=4))

    def save_changes(self):
        contents = self.detail_view.toPlainText()
        if len(contents) > 5:
            current_data = json.loads(contents, object_pairs_hook=MangaEntry)
            for i, entry in enumerate(self.mw.data):
                if entry.id == current_data['id']:
                    self.mw.data[i] = current_data
                    save_json(self.mw.data_file, self.mw.data)
                    self.mw.search_bar_handler.update_list()
                    break
