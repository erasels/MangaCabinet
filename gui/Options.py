from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QSlider, QVBoxLayout

search_thrshold = "search_cutoff_threshold"


def init_settings():
    return {search_thrshold: 100}


class OptionsDialog(QDialog):
    def __init__(self, parent=None, settings=None):
        super(OptionsDialog, self).__init__(parent)
        self.setWindowTitle("Options")

        # Use settings from parent or default if not provided
        self.settings = settings if settings else {search_thrshold: 100}

        self.init_ui()

    def init_ui(self):
        self.slider_label = QLabel(f"Search Cutoff Threshold: {self.settings['search_cutoff_threshold']}")

        # Add a QSlider for the threshold value
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(10, 250)
        self.slider.setValue(self.settings['search_cutoff_threshold'])
        self.slider.valueChanged.connect(self.slider_value_changed)

        # Layout management
        layout = QVBoxLayout()
        layout.addWidget(self.slider_label)
        layout.addWidget(self.slider)
        self.setLayout(layout)

    def slider_value_changed(self, value):
        self.settings[search_thrshold] = value
        self.slider_label.setText(f"Search Cutoff Threshold: {self.settings['search_cutoff_threshold']}")
