import os
import sys
import json

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QSize

from auxillary.JSONMethods import load_json, save_json, load_styles
from gui.ComboBoxDerivatives import RightClickableComboBox
from gui.MangaList import MangaDelegate
from gui.SearchBarHandler import SearchBarHandler
from gui.Options import OptionsDialog, init_settings, search_thrshold
from auxillary.DataAccess import MangaEntry


class MangaApp(QWidget):
    image_path = os.path.join('assets', 'images')
    data_path = os.path.join('assets', 'data')
    style_path = os.path.join('assets', 'styles')

    data_file = os.path.join(data_path, 'data_real.json')
    settings_file = os.path.join(data_path, 'settings.json')
    groups_file = os.path.join(data_path, 'groups.json')

    def __init__(self):
        super().__init__()
        self.data = load_json(MangaApp.data_file, data_type="mangas")
        self.groups = load_json(MangaApp.groups_file)
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
        search_box.addWidget(self.settings_button)
        search_box.addWidget(self.sort_combobox)
        self.layout.addLayout(search_box)

        # Groups bar
        self.group_combobox = RightClickableComboBox(self)
        self.group_combobox.addItem("None", None)
        for group_name, group_details in self.groups.items():
            self.group_combobox.addItem(group_name, group_name)

        self.group_combobox.currentIndexChanged.connect(lambda: self.search_bar_handler.update_list())
        self.group_combobox.rightClicked.connect(lambda: self.group_combobox.setCurrentIndex(0))
        self.group_combobox.setStyleSheet(self.styles.get("dropdown"))

        # Add group button
        self.add_group_btn = QPushButton("New Group", self)
        self.add_group_btn.clicked.connect(self.add_group)
        self.add_group_btn.setStyleSheet(self.styles.get("textbutton"))

        groups_box = QHBoxLayout()
        groups_box.addWidget(self.group_combobox, 1)
        groups_box.addWidget(self.add_group_btn)
        self.layout.addLayout(groups_box)

        # List view
        self.list_view = QListView(self)
        self.list_model = QStandardItemModel(self.list_view)
        self.list_view.setModel(self.list_model)

        self.list_view.setWrapping(True)
        self.list_view.setFlow(QListView.LeftToRight)
        self.list_view.setLayoutMode(QListView.Batched)

        self.list_delegate = MangaDelegate(self.list_view)
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

    # Method to add new group creation window
    def add_group(self):
        dialog = QDialog(self)
        layout = QVBoxLayout()

        # Name input
        name_label = QLabel("Group Name:", dialog)
        name_input = QLineEdit(dialog)
        name_input.setStyleSheet(self.styles.get("lineedit"))
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        # Color picker setup
        picked_color = [Qt.white]  # Default color, using a mutable type like a list to store the selected color
        pick_color_button = QPushButton("Pick Color", dialog)
        pick_color_button.setStyleSheet(self.styles.get("textbutton"))
        layout.addWidget(pick_color_button)

        # Update the button's background color to show the picked color
        def update_button_color(color):
            pick_color_button.setStyleSheet(f"background-color: {color.name()};")
            picked_color[0] = color

        pick_color_button.clicked.connect(lambda: update_button_color(QColorDialog.getColor()))

        # Save and Cancel buttons
        save_btn = QPushButton("Save", dialog)
        save_btn.clicked.connect(dialog.accept)
        save_btn.setStyleSheet(self.styles.get("textbutton"))
        cancel_btn = QPushButton("Cancel", dialog)
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet(self.styles.get("textbutton"))
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)

        result = dialog.exec_()
        if result == QDialog.Accepted:
            group_name = name_input.text()
            isNew = False
            if group_name not in self.groups:
                self.groups[group_name] = {}
                isNew = True
            self.groups[group_name].update({"color": picked_color[0].name()})
            save_json(MangaApp.groups_file, self.groups)
            if isNew:
                # Add to the combobox
                self.group_combobox.addItem(group_name, group_name)
            else:
                # Force refresh in case color changed
                self.search_bar_handler.update_list()

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
