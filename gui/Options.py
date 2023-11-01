import os

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QLabel, QSlider, QVBoxLayout, QCheckBox, QPushButton

from auxillary.JSONMethods import save_json, load_json

search_thrshold = "search_cutoff_threshold"
loose_match = "loose_search_matching"
multi_match = "count_multiple_matches"
bind_dview = "bind_detail_view"


def init_settings():
    return {
        search_thrshold: 100,
        loose_match: False,
        multi_match: False,
        bind_dview: True
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

        self.init_options_dialog()

    def get_widget(self):
        return self.settings_button

    # Method to create settings window
    def show_options_dialog(self):
        if self.exec_() == 0:
            self.mw.search_bar_handler.update_list()
            save_json(self.mw.settings_file, self.mw.settings)

    def init_options_dialog(self):
        self.slider_label = QLabel(self.get_search_cutoff_text())

        # Add a QSlider for the threshold value
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(self.mw.settings[search_thrshold])
        self.slider.valueChanged.connect(self.slider_value_changed)

        self.slider.setToolTip("The amount of results to return when using the search bar.")

        self.loose_match_checkbox = QCheckBox("Enable Loose Search Matching", self)
        self.loose_match_checkbox.setChecked(self.mw.settings[loose_match])
        self.loose_match_checkbox.stateChanged.connect(self.loose_match_changed)
        self.loose_match_checkbox.setToolTip("When enabled only one term of your search needs to match something to be returned.")

        self.multi_match_checkbox = QCheckBox("Enable Counting Matches", self)
        self.multi_match_checkbox.setChecked(self.mw.settings[multi_match])
        self.multi_match_checkbox.stateChanged.connect(self.multi_match_changed)
        self.multi_match_checkbox.setToolTip("When enabled results which contain a search term in multiple fields will have higher precedence, this becomes unintuitive with sorting.")

        self.bind_view_checkbox = QCheckBox("Bind Detail view to Editor", self)
        self.bind_view_checkbox.setChecked(self.mw.settings[bind_dview])
        self.bind_view_checkbox.stateChanged.connect(self.bind_view_changed)
        self.bind_view_checkbox.setToolTip("Update the detail view when selecting a manga from the list.")

        # Layout management
        layout = QVBoxLayout()
        layout.addWidget(self.slider_label)
        layout.addWidget(self.slider)
        layout.addWidget(self.loose_match_checkbox)
        layout.addWidget(self.multi_match_checkbox)
        layout.addWidget(self.bind_view_checkbox)
        self.setLayout(layout)

    def slider_value_changed(self, value):
        self.mw.settings[search_thrshold] = value
        self.slider_label.setText(self.get_search_cutoff_text())

    def get_search_cutoff_text(self):
        return f"Search Cutoff Threshold: {self.mw.settings[search_thrshold] if self.mw.settings[search_thrshold] else 'Unlimited'}"

    def loose_match_changed(self, state):
        self.mw.settings[loose_match] = bool(state)

    def multi_match_changed(self, state):
        self.mw.settings[multi_match] = bool(state)

    def bind_view_changed(self, state):
        self.mw.settings[bind_dview] = bool(state)
        self.bindViewChanged.emit(bool(state))
