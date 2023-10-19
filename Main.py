import os
import sys
import json

from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLineEdit, QListWidget, QPushButton, QTextEdit, QDialog, \
    QSlider, QLabel, QHBoxLayout, QComboBox, QListWidgetItem, QColorDialog, QMessageBox
from PyQt5.QtCore import Qt, QSize
from fuzzywuzzy import fuzz

from gui.ComboBoxDerivatives import CustomComboBox


class MangaApp(QWidget):
    data_file = os.path.join('assets', 'data', 'data.json')
    settings_file = os.path.join('assets', 'data', 'settings.json')
    groups_file = os.path.join('assets', 'data', 'groups.json')

    def __init__(self):
        super().__init__()
        self.data = self.load_json(MangaApp.data_file)
        self.groups = self.load_json(MangaApp.groups_file)
        self.showing_all_entries = False
        self.search_cutoff_threshold = 0
        self.sort_order_reversed = False
        self.load_settings()
        self.init_ui()

    def load_json(self, file_path: str, data_type='list'):
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                try:
                    return json.load(file)
                except json.JSONDecodeError:
                    print(f"Warning: The file {file_path} contains invalid JSON. Using default {data_type} instead.")
                    return [] if data_type == 'list' else {}
        else:
            print(f"Warning: The file {file_path} does not exist. Using default {data_type} instead.")
            return [] if data_type == 'list' else {}

    def save_json(self, file_path: str, input_data):
        with open(file_path, 'w') as file:
            json.dump(input_data, file, indent=4)

    def load_settings(self):
        settings = self.load_json(MangaApp.settings_file, "dict")
        self.search_cutoff_threshold = settings.get("search_cutoff_threshold", 100)

    def save_settings(self):
        settings = {"search_cutoff_threshold": self.search_cutoff_threshold}
        self.save_json(MangaApp.settings_file, settings)

    def init_ui(self):
        self.layout = QVBoxLayout()

        # Search bar
        self.search_bar = QLineEdit(self)
        self.search_bar.textChanged.connect(self.update_list)

        # Options Button
        self.settings_button = QPushButton(self)
        self.settings_button.setIcon(QIcon('assets/images/options_icon.png'))
        self.settings_button.setIconSize(QSize(24, 24))
        self.settings_button.setFixedSize(24, 24)  # Set the button size to match the icon size
        self.settings_button.setStyleSheet("QPushButton { border: none; }")  # Remove button styling
        self.settings_button.clicked.connect(self.show_options_dialog)

        # Sort drop down
        self.sort_combobox = CustomComboBox()
        self.sorting_options = [
            ("By id", lambda entry: entry['id']),
            ("By date added", lambda entry: self.data.index(entry)),
            ("By score", lambda entry: entry.get('score', float('-inf')))
        ]
        for name, _ in self.sorting_options:
            self.sort_combobox.addItem(name)
        self.sort_combobox.currentIndexChanged.connect(lambda: self.update_list(forceRefresh=True))
        self.sort_combobox.rightClicked.connect(self.toggle_sort_order)

        search_box = QHBoxLayout()  # Create a horizontal box layout
        search_box.addWidget(self.search_bar, 1)  # The '1' makes the search bar expand to fill available space
        search_box.addWidget(self.settings_button)
        search_box.addWidget(self.sort_combobox)
        self.layout.addLayout(search_box)

        # Groups bar
        self.group_combobox = CustomComboBox(self)
        self.group_combobox.addItem("None", None)
        for group_name, group_details in self.groups.items():
            self.group_combobox.addItem(group_name, group_name)

        self.group_combobox.currentIndexChanged.connect(lambda: self.update_list(forceRefresh=True))
        self.group_combobox.rightClicked.connect(lambda: self.group_combobox.setCurrentIndex(0))

        # Add group button
        self.add_group_btn = QPushButton("Add Group", self)
        self.add_group_btn.clicked.connect(self.add_group)

        groups_box = QHBoxLayout()
        groups_box.addWidget(self.group_combobox, 1)
        groups_box.addWidget(self.add_group_btn)
        self.layout.addLayout(groups_box)

        # List view
        self.list_widget = QListWidget(self)
        self.list_widget.itemClicked.connect(self.display_detail)
        self.layout.addWidget(self.list_widget)
        self.update_list()

        # Detail view (as a text edit for simplicity)
        self.detail_view = QTextEdit(self)
        self.layout.addWidget(self.detail_view)

        # Save button
        self.save_button = QPushButton("Save Changes", self)
        self.save_button.clicked.connect(self.save_changes)
        self.layout.addWidget(self.save_button)

        self.setLayout(self.layout)

    def toggle_sort_order(self):
        print(f"Toggling sort order from: {self.sort_order_reversed}")
        self.sort_order_reversed = not self.sort_order_reversed
        self.update_list(forceRefresh=True)

    def secondary_sort_key(self, x):
        sort_func = self.sorting_options[self.sort_combobox.currentIndex()][1]
        return sort_func(x[0])

    # Method to create settings window
    def show_options_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Options")

        self.slider_label = QLabel(f"Search Cutoff Threshold: {self.search_cutoff_threshold}")

        # Add a QSlider for the threshold value
        self.slider = QSlider(Qt.Horizontal, dialog)
        self.slider.setRange(10, 250)
        self.slider.setValue(self.search_cutoff_threshold)  # Convert to percentage
        self.slider.valueChanged.connect(self.slider_value_changed)

        # Layout management
        layout = QVBoxLayout()
        layout.addWidget(self.slider_label)
        layout.addWidget(self.slider)
        dialog.setLayout(layout)

        dialog.exec_()

    # Method to add new group creation window
    def add_group(self):
        dialog = QDialog(self)
        layout = QVBoxLayout()

        # Name input
        name_label = QLabel("Group Name:", dialog)
        name_input = QLineEdit(dialog)
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        # Color picker setup
        picked_color = [Qt.white]  # Default color, using a mutable type like a list to store the selected color
        pick_color_button = QPushButton("Pick Color", dialog)
        layout.addWidget(pick_color_button)

        # Update the button's background color to show the picked color
        def update_button_color(color):
            pick_color_button.setStyleSheet(f"background-color: {color.name()};")
            picked_color[0] = color

        pick_color_button.clicked.connect(lambda: update_button_color(QColorDialog.getColor()))

        # Save and Cancel buttons
        save_btn = QPushButton("Save", dialog)
        save_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Cancel", dialog)
        cancel_btn.clicked.connect(dialog.reject)
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
            self.save_json(MangaApp.groups_file, self.groups)
            if isNew:
                # Add to the combobox
                self.group_combobox.addItem(group_name, group_name)
            else:
                # Force refresh in case color changed
                self.update_list(forceRefresh=True)

    def slider_value_changed(self, value):
        self.search_cutoff_threshold = value
        self.slider_label.setText(f"Search Cutoff Threshold: {self.search_cutoff_threshold}")
        self.save_settings()  # Save to the settings.json file

    def match_score(self, data, terms):
        """Compute a score based on the number of matching terms."""
        score = 0

        for term in terms:
            if ":" in term:
                field, value = term.split(":", 1)
                data_value = data.get(field, "")
                if isinstance(data_value, (int, float)):
                    if str(data_value) == value:
                        score += 1
                elif value.lower() in str(data_value).lower():
                    score += 1
            else:
                if any(term.lower() in str(data_value).lower() for data_value in data.values()):
                    score += 1

        return score

    def update_list(self, forceRefresh=False):
        search_terms = [term.strip() for term in self.search_bar.text().split(",")]

        # Define sort in case we need it
        _, sort_func = self.sorting_options[self.sort_combobox.currentIndex()]
        selected_group = self.group_combobox.currentData()

        if not selected_group:
            mod_data = self.data
        else:
            # TODO: Inefficient, might need to be optimized
            mod_data = [manga_entry for manga_entry in self.data if manga_entry.get("MC_Grouping") == selected_group]

        # If less than 3 characters and already showing all entries, return early
        if len(search_terms) < 3:
            if self.showing_all_entries and not forceRefresh:
                return
            else:
                sorted_data = sorted(mod_data, key=lambda x: sort_func(x), reverse=not self.sort_order_reversed)
                self.list_widget.clear()
                for entry in sorted_data:
                    self.list_widget.addItem(self.create_list_item(entry))
                self.showing_all_entries = True
                return

        # Compute scores for all manga entries and sort them based on the score
        scored_data = [(entry, self.match_score(entry, search_terms)) for entry in mod_data]
        sorted_data = sorted(scored_data, key=lambda x: (-x[1], self.secondary_sort_key(x)), reverse=not self.sort_order_reversed)

        self.list_widget.clear()  # Clear the list before adding filtered results

        for idx, (entry, score) in enumerate(sorted_data):
            if score == len(search_terms) and idx < self.search_cutoff_threshold:
                self.list_widget.addItem(self.create_list_item(entry))
            else:
                break

        self.showing_all_entries = False

    def create_list_item(self, entry: dict):
        item = QListWidgetItem(entry['title'])
        group_name = entry.get('MC_Grouping')
        if group_name and group_name in self.groups:
            color = self.groups[group_name].get("color")
            if color:
                item.setBackground(QColor(color))

        return item

    def display_detail(self, item):
        title = item.text()
        for entry in self.data:
            if entry['title'] == title:
                self.detail_view.setText(json.dumps(entry, indent=4))

    def save_changes(self):
        if self.detail_view.toPlainText():
            current_data = json.loads(self.detail_view.toPlainText())
            for i, entry in enumerate(self.data):
                if entry['title'] == current_data['title']:
                    self.data[i] = current_data
                    self.save_json(MangaApp.data_file, self.data)
                    self.update_list()
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
    window.resize(400, 400)
    window.show()
    sys.exit(app.exec_())
