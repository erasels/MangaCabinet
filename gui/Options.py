from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QSlider, QVBoxLayout, QCheckBox

search_thrshold = "search_cutoff_threshold"
loose_match = "loose_search_matching"


def init_settings():
    return {
        search_thrshold: 100,
        loose_match: False
    }


class OptionsDialog(QDialog):
    def __init__(self, parent):
        super(OptionsDialog, self).__init__(parent)
        self.setWindowTitle("Options")

        self.mw = self.parent()

        self.init_ui()

    def init_ui(self):
        self.slider_label = QLabel(self.get_search_cutoff_text())

        # Add a QSlider for the threshold value
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(self.mw.settings[search_thrshold])
        self.slider.valueChanged.connect(self.slider_value_changed)

        tooltip_text = "The amount of results to return when using the search bar."
        self.slider.setToolTip(tooltip_text)

        # Add a QCheckBox for the loose search matching option
        self.loose_match_checkbox = QCheckBox("Enable Loose Search Matching", self)
        self.loose_match_checkbox.setChecked(self.mw.settings[loose_match])
        self.loose_match_checkbox.stateChanged.connect(self.loose_match_changed)

        tooltip_text = "When enabled only one term of your search needs to match something to be returned."
        self.loose_match_checkbox.setToolTip(tooltip_text)

        # Layout management
        layout = QVBoxLayout()
        layout.addWidget(self.slider_label)
        layout.addWidget(self.slider)
        layout.addWidget(self.loose_match_checkbox)  # Add the checkbox to the layout
        self.setLayout(layout)

    def slider_value_changed(self, value):
        self.mw.settings[search_thrshold] = value
        self.slider_label.setText(self.get_search_cutoff_text())

    def get_search_cutoff_text(self):
        return f"Search Cutoff Threshold: {self.mw.settings[search_thrshold] if self.mw.settings[search_thrshold] else 'All'}"

    def loose_match_changed(self, state):
        self.mw.settings[loose_match] = bool(state)
