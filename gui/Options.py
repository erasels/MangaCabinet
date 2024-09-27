import os

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QLabel, QSlider, QVBoxLayout, QCheckBox, QPushButton, QComboBox, QHBoxLayout, QFileDialog, QGroupBox

from auxillary.JSONMethods import save_json, load_json

show_removed = "show_removed_entries"
show_on_disk = "show_system_location_indicator"
show_language = "show_manga_language_indicator"
default_sort = "default_sort_option"
search_thrshold = "search_cutoff_threshold"
bind_dview = "bind_detail_view"
thumbnail_preview = "show_hover_thumbnail"
thumbnail_delegate = "use_thumbnail_view"
download_script_loc = "download_script_location"
default_manga_loc = "default_manga_system_location"
prefer_open_on_disk = "open_manga_on_filesystem_first"


def init_settings():
    return {
        show_removed: False,
        show_on_disk: False,
        show_language: True,
        default_sort: "By data order",
        search_thrshold: 100,
        bind_dview: False,
        thumbnail_preview: True,
        thumbnail_delegate: False,
        default_manga_loc: "",
        prefer_open_on_disk: True
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
        self.settings_button.setStyleSheet("""QPushButton { border: none; }
            QPushButton:hover { background-color: #cccccc; border-radius: 10px;}""")
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
        # Group for list view settings
        list_view_group = QGroupBox("List View Options", self)
        list_view_layout = QVBoxLayout(list_view_group)
        self.show_removed_checkbox = QCheckBox("Show Mangas Marked as Removed", list_view_group)
        self.show_removed_checkbox.setChecked(self.mw.settings[show_removed])
        self.show_removed_checkbox.stateChanged.connect(lambda state: self.simple_change(show_removed, state))
        self.show_removed_checkbox.setToolTip("Show removed entries in the main manga list.")

        self.show_language_checkbox = QCheckBox("Show Language Indicator", list_view_group)
        self.show_language_checkbox.setChecked(self.mw.settings[show_language])
        self.show_language_checkbox.stateChanged.connect(lambda state: self.simple_change(show_language, state))
        self.show_language_checkbox.setToolTip("Show a language flag icon in thumbnail view.")

        self.default_sort_label = QLabel("Default Sort:", list_view_group)
        self.default_sort_combobox = QComboBox(list_view_group)
        sort_options = [name for name, _, _ in self.mw.search_bar_handler.sorting_options]
        self.default_sort_combobox.addItems(sort_options)
        current_sort_index = sort_options.index(self.mw.settings.get(default_sort, sort_options[0]))
        self.default_sort_combobox.setCurrentIndex(current_sort_index)
        self.default_sort_combobox.currentIndexChanged.connect(self.set_default_sort_option)
        self.default_sort_combobox.setStyleSheet(self.mw.styles.get("dropdown"))
        self.default_sort_combobox.setToolTip("Select the default sort option for the manga list.")

        self.slider_label = QLabel(self.get_search_cutoff_text(), list_view_group)
        self.slider = QSlider(Qt.Horizontal, list_view_group)
        self.slider.setRange(0, 30)
        self.slider.setValue(int(self.mw.settings[search_thrshold] * 0.1))
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.slider.setToolTip("The amount of results to return when using the search bar.")

        list_view_layout.addWidget(self.show_removed_checkbox)
        list_view_layout.addWidget(self.show_language_checkbox)
        list_view_layout.addWidget(self.default_sort_label)
        list_view_layout.addWidget(self.default_sort_combobox)
        list_view_layout.addWidget(self.slider_label)
        list_view_layout.addWidget(self.slider)

        # Group for thumbnails settings
        thumbnails_group = QGroupBox("Thumbnails Options", self)
        thumbnails_layout = QVBoxLayout(thumbnails_group)
        self.bind_view_checkbox = QCheckBox("Bind Detail View to Editor", thumbnails_group)
        self.bind_view_checkbox.setChecked(self.mw.settings[bind_dview])
        self.bind_view_checkbox.stateChanged.connect(self.bind_view_changed)
        self.bind_view_checkbox.setToolTip("Update the detail view when selecting a manga from the list.")

        self.thumbnail_checkbox = QCheckBox("Show Thumbnail on Hover", thumbnails_group)
        self.thumbnail_checkbox.setChecked(self.mw.settings[thumbnail_preview])
        self.thumbnail_checkbox.stateChanged.connect(lambda state: self.simple_change(thumbnail_preview, state))
        self.thumbnail_checkbox.setToolTip("Whether to show the thumbnail of the manga you're hovering in the manga list. Not that useful if the thumbnail view is used.")

        self.switch_delegate_checkbox = QCheckBox("Use Thumbnail List View", thumbnails_group)
        self.switch_delegate_checkbox.setChecked(self.mw.settings[thumbnail_delegate])
        self.switch_delegate_checkbox.stateChanged.connect(self.thumbnail_view_changed)
        self.switch_delegate_checkbox.setToolTip("WARNING: High RAM requirement if you have a lot of mangas with thumbnails.")

        thumbnails_layout.addWidget(self.bind_view_checkbox)
        thumbnails_layout.addWidget(self.thumbnail_checkbox)
        thumbnails_layout.addWidget(self.switch_delegate_checkbox)

        # Group for local settings
        local_group = QGroupBox("Local Manga Options", self)
        local_layout = QVBoxLayout(local_group)
        self.default_manga_label = QLabel("Default Manga Location:", self)
        self.default_manga_loc_label = QLabel(self.truncate_path(self.mw.settings.get(default_manga_loc, 'Not set')), self)
        self.default_manga_loc_label.setToolTip(self.mw.settings[default_manga_loc])
        self.default_manga_loc_button = QPushButton("Change Location", self)
        self.default_manga_loc_button.setStyleSheet(self.mw.styles.get("textbutton"))
        self.default_manga_loc_button.setToolTip("Location you keep your mangas named after the id of the entry. If selected, will check for mangas in there on startup.")
        self.default_manga_loc_button.clicked.connect(self.change_default_manga_loc)

        self.show_on_disk_checkbox = QCheckBox("Show Local Copy Indicator", local_group)
        self.show_on_disk_checkbox.setChecked(self.mw.settings[show_on_disk])
        self.show_on_disk_checkbox.stateChanged.connect(lambda state: self.simple_change(show_on_disk, state))
        self.show_on_disk_checkbox.setToolTip("Show a folder icon in thumbnail view when the manga has been located on your system.")

        self.prefer_disk_checkbox = QCheckBox("Prefer Opening Manga Folder over Browser", local_group)
        self.prefer_disk_checkbox.setChecked(self.mw.settings[prefer_open_on_disk])
        self.prefer_disk_checkbox.stateChanged.connect(lambda state: self.simple_change(prefer_open_on_disk, state))
        self.prefer_disk_checkbox.setToolTip("When middle-clicking a manga in the list, try to open it in the explorer/reader app if possible, otherwise in browser.")

        local_layout.addWidget(self.default_manga_label)
        local_layout.addWidget(self.default_manga_loc_label)
        local_layout.addWidget(self.default_manga_loc_button)
        local_layout.addWidget(self.show_on_disk_checkbox)
        local_layout.addWidget(self.prefer_disk_checkbox)

        # Apply the style to the group boxes
        group_box_style = self.mw.styles.get("groupbox")
        list_view_group.setStyleSheet(group_box_style)
        thumbnails_group.setStyleSheet(group_box_style)
        local_group.setStyleSheet(group_box_style)

        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(list_view_group)
        layout.addWidget(thumbnails_group)
        layout.addWidget(local_group)
        self.setLayout(layout)

    def slider_value_changed(self, value):
        self.mw.settings[search_thrshold] = value * 10
        self.slider_label.setText(self.get_search_cutoff_text())

    def get_search_cutoff_text(self):
        return f"Search Cutoff Threshold: {self.mw.settings[search_thrshold] if self.mw.settings[search_thrshold] else 'Unlimited'}"

    def simple_change(self, setting, state):
        self.mw.settings[setting] = bool(state)

    def bind_view_changed(self, state):
        self.mw.settings[bind_dview] = bool(state)
        self.bindViewChanged.emit(bool(state))

    def thumbnail_view_changed(self, state):
        self.mw.settings[thumbnail_delegate] = bool(state)
        self.mw.manga_list_handler.switch_delegate(bool(state))

    def set_default_sort_option(self, index):
        sort_option = self.mw.search_bar_handler.sorting_options[index][0]
        self.mw.settings[default_sort] = sort_option

    def change_default_manga_loc(self):
        options = QFileDialog.Options()
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self.mw.settings[default_manga_loc], options=options)
        if folder:
            self.mw.settings[default_manga_loc] = folder
            self.default_manga_loc_label.setText(self.truncate_path(folder))
            self.default_manga_loc_label.setToolTip(folder)
            self.mw.disk_handler.check_entries_disk_locations(self.mw.data, loose_check=False)

    def truncate_path(self, path, max_length=50):
        return path if len(path) <= max_length else '...' + path[-max_length + 3:]
