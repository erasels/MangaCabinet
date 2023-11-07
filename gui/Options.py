import os

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QLabel, QSlider, QVBoxLayout, QCheckBox, QPushButton, QComboBox, QHBoxLayout

from auxillary.JSONMethods import save_json, load_json

show_removed = "show_removed_entries"
default_sort = "default_sort_option"
search_thrshold = "search_cutoff_threshold"
loose_match = "loose_search_matching"
multi_match = "count_multiple_matches"
bind_dview = "bind_detail_view"
thumbnail_preview = "show_hover_thumbnail"


def init_settings():
    return {
        show_removed: False,
        default_sort: "By data order",
        search_thrshold: 100,
        loose_match: False,
        multi_match: False,
        bind_dview: False,
        thumbnail_preview: True
    }


def load_settings(settings_path):
    settings = load_json(settings_path, "dict")
    if settings:
        return settings
    else:
        return init_settings()


class OptionsHandler(QDialog):
    bindViewChanged = pyqtSignal(bool)

    def __init__(self, parent):
        super(OptionsHandler, self).__init__(parent)
        self.settings_button = None
        self.dialog = None
        self.setup = False
        self.setWindowTitle("Options")

        self.mw = self.parent()

        self.init_ui()

    # Create Options Dialog
    def init_ui(self):
        # Options Button
        self.settings_button = QPushButton(self)
        self.settings_button.setIcon(QIcon(os.path.join(self.mw.image_path, 'options_icon.png')))
        self.settings_button.setIconSize(QSize(24, 24))
        self.settings_button.setFixedSize(24, 24)  # Set the button size to match the icon size
        self.settings_button.setStyleSheet("QPushButton { border: none; }")  # Remove button styling
        self.settings_button.clicked.connect(self.show_options_dialog)

        self.settings_button.setToolTip("Options")

    def get_widget(self):
        return self.settings_button

    # Method to create settings window
    def show_options_dialog(self):
        if not self.setup:
            self.init_options_dialog()
            self.setup = True

        if self.exec_() == 0:
            self.mw.search_bar_handler.update_list()
            save_json(self.mw.settings_file, self.mw.settings)

    def init_options_dialog(self):
        self.show_removed_checkbox = QCheckBox("Show Removed Entries", self)
        self.show_removed_checkbox.setChecked(self.mw.settings[show_removed])
        self.show_removed_checkbox.stateChanged.connect(lambda state: self.simple_change(show_removed, state))
        self.show_removed_checkbox.setToolTip("Show removed entries in the main manga list.")

        self.default_sort_label = QLabel("Default Sort:", self)

        self.default_sort_combobox = QComboBox(self)
        sort_options = [name for name, _, _ in self.mw.search_bar_handler.sorting_options]
        self.default_sort_combobox.addItems(sort_options)
        current_sort_index = sort_options.index(self.mw.settings.get(default_sort, sort_options[0]))
        self.default_sort_combobox.setCurrentIndex(current_sort_index)
        self.default_sort_combobox.currentIndexChanged.connect(self.set_default_sort_option)
        self.default_sort_combobox.setStyleSheet(self.mw.styles.get("dropdown"))
        self.default_sort_combobox.setToolTip("Select the default sort option for the manga list.")

        self.slider_label = QLabel(self.get_search_cutoff_text())
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(self.mw.settings[search_thrshold])
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.slider.setToolTip("The amount of results to return when using the search bar.")

        self.loose_match_checkbox = QCheckBox("Enable Loose Search Matching", self)
        self.loose_match_checkbox.setChecked(self.mw.settings[loose_match])
        self.loose_match_checkbox.stateChanged.connect(lambda state: self.simple_change(loose_match, state))
        self.loose_match_checkbox.setToolTip("When enabled only one term of your search needs to match something to be returned.")

        self.multi_match_checkbox = QCheckBox("Enable Counting Matches", self)
        self.multi_match_checkbox.setChecked(self.mw.settings[multi_match])
        self.multi_match_checkbox.stateChanged.connect(lambda state: self.simple_change(multi_match, state))
        self.multi_match_checkbox.setToolTip("When enabled results which contain a search term in multiple fields will have higher precedence, this becomes unintuitive with sorting.")

        self.bind_view_checkbox = QCheckBox("Bind Detail View to Editor", self)
        self.bind_view_checkbox.setChecked(self.mw.settings[bind_dview])
        self.bind_view_checkbox.stateChanged.connect(self.bind_view_changed)
        self.bind_view_checkbox.setToolTip("Update the detail view when selecting a manga from the list.")

        self.thumbnail_checkbox = QCheckBox("Show Thumbnail on Hover", self)
        self.thumbnail_checkbox.setChecked(self.mw.settings[thumbnail_preview])
        self.thumbnail_checkbox.stateChanged.connect(lambda state: self.simple_change(thumbnail_preview, state))

        sort_layout = QHBoxLayout()
        sort_layout.addWidget(self.default_sort_label)
        sort_layout.addWidget(self.default_sort_combobox)

        # Layout management
        layout = QVBoxLayout()
        layout.addWidget(self.show_removed_checkbox)
        layout.addLayout(sort_layout)
        layout.addWidget(self.slider_label)
        layout.addWidget(self.slider)
        layout.addWidget(self.loose_match_checkbox)
        layout.addWidget(self.multi_match_checkbox)
        layout.addWidget(self.bind_view_checkbox)
        layout.addWidget(self.thumbnail_checkbox)
        self.setLayout(layout)

    def slider_value_changed(self, value):
        self.mw.settings[search_thrshold] = value
        self.slider_label.setText(self.get_search_cutoff_text())

    def get_search_cutoff_text(self):
        return f"Search Cutoff Threshold: {self.mw.settings[search_thrshold] if self.mw.settings[search_thrshold] else 'Unlimited'}"

    def simple_change(self, setting, state):
        self.mw.settings[setting] = bool(state)

    def bind_view_changed(self, state):
        self.mw.settings[bind_dview] = bool(state)
        self.bindViewChanged.emit(bool(state))

    def set_default_sort_option(self, index):
        sort_option = self.mw.search_bar_handler.sorting_options[index][0]
        self.mw.settings[default_sort] = sort_option
