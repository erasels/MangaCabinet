import json
import logging
import os

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QTextEdit, QPushButton, QGridLayout, QLineEdit, QLabel, QWidget, QComboBox, \
    QHBoxLayout

from auxillary.DataAccess import MangaEntry
from gui.Options import bind_dview
from gui.WidgetDerivatives import CustomTextEdit, IdMatcher, TagsWidget


class DetailEditorHandler:
    def __init__(self, parent):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.cur_data = None
        self.save_button = None
        self.detail_view = None
        self.mw = parent
        self.json_edit_mode = False
        self.current_row = 0
        self.current_col = 0

        self.img_empty_star = os.path.join(self.mw.image_path, 'star_empty.png')
        self.img_star = os.path.join(self.mw.image_path, 'star.png')

        self.init_ui()

    def init_ui(self):
        # Detail view
        self.detail_view = QTextEdit(self.mw)
        self.detail_view.setPlaceholderText("Select an item to edit it.")
        self.detail_view.hide()

        # Save button
        self.save_button = QPushButton("Save Changes", self.mw)
        self.save_button.clicked.connect(self.save_changes)
        self.save_button.setStyleSheet(self.mw.styles.get("textbutton"))
        self.save_button.hide()

        self.layout = QGridLayout()

        # Title and Short Title
        self.title_input = QLineEdit(self.mw)
        self.title_input.setStyleSheet(self.mw.styles.get("lineedit"))
        self.title_input.textChanged.connect(lambda: self.title_input.setToolTip(self.title_input.text()))
        self.title_input.editingFinished.connect(self.save_changes)
        self.short_title_input = QLineEdit(self.mw)
        self.short_title_input.setStyleSheet(self.mw.styles.get("lineedit"))
        self.short_title_input.setPlaceholderText("Input shorter title for displaying")
        self.short_title_input.textChanged.connect(
            lambda: self.short_title_input.setToolTip(self.short_title_input.text()))
        self.short_title_input.editingFinished.connect(self.save_changes)

        # Create a new QHBoxLayout for the titles
        titles_layout = QHBoxLayout()

        titles_layout.addWidget(QLabel("Title:"), 0)
        titles_layout.addWidget(self.title_input, 2)  # Give 3 parts of space to title_input
        titles_layout.addWidget(QLabel("Short Title:"), 0)
        titles_layout.addWidget(self.short_title_input, 1)  # Give 1 part of space to short_title_input

        # Add the horizontal layout to the main grid layout
        self.layout.addLayout(titles_layout, 0, 0, 1, 4)  # Span it across 4 columns

        # Tags Area with QGridLayout
        self.tags_widget = TagsWidget(self.mw)
        self.tags_widget.saveSignal.connect(self.save_changes)
        self.layout.addWidget(self.tags_widget, 1, 1)

        # Similar entry selector
        self.similar_searcher = IdMatcher(self.mw)
        self.similar_searcher.saveSignal.connect(self.save_changes)
        self.layout.addWidget(self.similar_searcher, 1, 3, 1, 1)

        # Description
        self.description_input = CustomTextEdit(self.mw)
        self.description_input.setMaximumHeight(80)
        self.description_input.setStyleSheet(self.mw.styles.get("textedit"))
        self.description_input.setPlaceholderText("Input description which can be searched")
        self.description_input.contentEdited.connect(self.save_changes)
        self.layout.addWidget(QLabel("Description:"), 2, 0)
        self.layout.addWidget(self.description_input, 2, 1, 1, 3)  # Span over three columns

        # Layout for misc data
        misc_layout = QHBoxLayout()

        # Score
        self.score_widget = QWidget(self.mw)
        self.score_layout = QHBoxLayout(self.score_widget)
        self.stars = []
        for i in range(5):
            star_label = QLabel(self.score_widget)
            pixmap = QPixmap(self.img_empty_star)
            star_label.setPixmap(pixmap)
            star_label.mousePressEvent = lambda event, i=i: self.set_score(i + 1)
            self.score_layout.addWidget(star_label)
            self.stars.append(star_label)

        misc_layout.addWidget(QLabel("Score:"), 0)
        misc_layout.addWidget(self.score_widget, 1)

        # Group
        self.group_combobox = QComboBox(self.mw)
        self.group_combobox.setStyleSheet(self.mw.styles.get("dropdown"))
        self.group_combobox.currentIndexChanged.connect(self.save_changes)
        misc_layout.addWidget(QLabel("Group:"), 0)
        misc_layout.addWidget(self.group_combobox, 1)

        # Language and Artist
        self.language_input = QLineEdit(self.mw)
        self.artist_input = QLineEdit(self.mw)
        self.language_input.setStyleSheet(self.mw.styles.get("lineedit"))
        self.language_input.setPlaceholderText("Input languages here (csv)")
        self.language_input.editingFinished.connect(self.save_changes)

        self.artist_input.setStyleSheet(self.mw.styles.get("lineedit"))
        self.artist_input.setPlaceholderText("Input artists/groups here (csv)")
        self.artist_input.editingFinished.connect(self.save_changes)

        misc_layout.addWidget(QLabel("Artists:"), 0)
        misc_layout.addWidget(self.artist_input, 1)
        misc_layout.addWidget(QLabel("Languages:"), 0)
        misc_layout.addWidget(self.language_input, 1)

        # Don't cover the edit button
        misc_layout.insertSpacing(8, 50)
        self.layout.addLayout(misc_layout, 3, 0, 1, 4)

        # Toggle edit mode button
        self.toggle_button = QPushButton(self.mw)
        self.toggle_button.setIcon(QIcon(os.path.join(self.mw.image_path, 'edit_icon.png')))
        self.toggle_button.setIconSize(QSize(41, 41))
        self.toggle_button.setFixedSize(41, 41)
        self.toggle_button.setStyleSheet("QPushButton { border: none; }")
        self.toggle_button.setToolTip("Switch between json editing and easy edit.")
        self.positionToggleButton()
        self.toggle_button.clicked.connect(self.toggle_edit_mode)
        self.toggle_button.raise_()

    # Json edit
    def get_widgets(self):
        return self.detail_view, self.save_button

    # For the details display
    def get_layout(self):
        return self.layout

    def handle_resize(self):
        self.positionToggleButton()

    def positionToggleButton(self):
        """Position the button in the bottom right corner of the window."""
        button_width = self.toggle_button.width()
        button_height = self.toggle_button.height()
        x_position = self.mw.width() - button_width - 10
        y_position = self.mw.height() - button_height - 10
        self.toggle_button.setGeometry(x_position, y_position, button_width, button_height)

    def display_detail(self, index, reload=False):
        if not reload:
            new_data = index.data(Qt.UserRole)
            if self.cur_data == new_data:
                if self.mw.settings[bind_dview]:
                    self.mw.open_detail_view(self.cur_data)
                return
            self.cur_data = new_data
        if not self.cur_data:
            return

        if self.mw.settings[bind_dview]:
            self.mw.open_detail_view(self.cur_data)

        if self.json_edit_mode:
            self.detail_view.setText(json.dumps(self.cur_data, indent=4))
        else:
            # Populate fields with manga data
            self.title_input.setText(self.cur_data.title)
            self.short_title_input.setText(self.cur_data.title_short)

            self.tags_widget.load_tags(self.cur_data.tags)

            self.description_input.setText(self.cur_data.description)
            self.language_input.setText(", ".join(self.cur_data.language))
            self.artist_input.setText(", ".join(self.cur_data.artist))

            self.set_score(self.cur_data.score, saveChange=False)

            self.similar_searcher.load(self.cur_data)

            self.group_combobox.blockSignals(True)
            self.group_combobox.clear()
            self.group_combobox.addItem("None")
            for group_name in self.mw.group_handler.groups.keys():
                self.group_combobox.addItem(group_name)
            current_group = self.cur_data.group
            if current_group in self.mw.group_handler.groups:
                self.group_combobox.setCurrentText(current_group)
            self.group_combobox.blockSignals(False)

    def save_changes(self):
        if not self.cur_data:
            return

        if self.mw.settings[bind_dview]:
            self.mw.open_detail_view(self.cur_data)

        if self.json_edit_mode:
            contents = self.detail_view.toPlainText()
            if len(contents) > 5:  # saftey to not save bogus
                modified_data = json.loads(contents, object_pairs_hook=MangaEntry)
                self.cur_data.clear()  # Done to update inplace references
                self.cur_data.update(modified_data)
                self.mw.is_data_modified = True
                self.mw.search_bar_handler.update_list()
        else:
            data_changed = False

            def update_attribute(attr, new_value):
                nonlocal data_changed

                old_value = getattr(self.cur_data, attr)

                # Check if old and new values are lists and normalize empty string lists
                if isinstance(old_value, list) and isinstance(new_value, list):
                    old_value = [item for item in old_value if item]
                    new_value = [item for item in new_value if item]

                if old_value != new_value:
                    setattr(self.cur_data, attr, new_value)
                    self.logger.debug(f"{self.cur_data.id}: {attr} was updated with: {new_value}")
                    data_changed = True

            attributes_mapping = {
                'title': self.title_input.text,
                'title_short': self.short_title_input.text,
                'tags': self.tags_widget.extract_tags_from_layout,
                'description': self.description_input.toPlainText,
                'language': lambda: [lang.strip() for lang in self.language_input.text().split(",")],
                'artist': lambda: [artist.strip() for artist in self.artist_input.text().split(",")],
                'score': self.get_current_score,
                'similar': lambda: self.similar_searcher.selected_items
            }

            for attr, func in attributes_mapping.items():
                update_attribute(attr, func())

            # Special case for the group combobox
            group_value = self.group_combobox.currentText()
            if group_value == "None":
                if self.cur_data.group:
                    self.logger.debug(f"{self.cur_data.id}: group was updated with: deleted value")
                    delattr(self.cur_data, 'group')
                    data_changed = True
            else:
                update_attribute('group', group_value)

            if data_changed:
                self.mw.is_data_modified = True
                self.mw.search_bar_handler.update_list()

    def set_score(self, score, saveChange=True):
        for i, star_label in enumerate(self.stars):
            pixmap = QPixmap(self.img_star if i < score else self.img_empty_star)
            star_label.setPixmap(pixmap)
        if saveChange:
            self.save_changes()

    def get_current_score(self):
        for i, star_label in enumerate(self.stars):
            # When an empty star is found, return i (because we start counting from 1)
            if star_label.pixmap().cacheKey() == QPixmap(self.img_empty_star).cacheKey():
                return i
        # If no empty stars were found, it means a score of 5.
        return 5

    def toggle_edit_mode(self):
        if not self.json_edit_mode:
            for i in range(self.layout.count()):
                self.recursively_toggle_visibility(self.layout.itemAt(i), False)
            self.detail_view.show()
            self.save_button.show()
        else:
            self.detail_view.hide()
            self.save_button.hide()
            for i in range(self.layout.count()):
                self.recursively_toggle_visibility(self.layout.itemAt(i), True)

        self.json_edit_mode = not self.json_edit_mode
        self.display_detail(0, True)  # Index is skipped

    def recursively_toggle_visibility(self, item, show: bool):
        """Toggle the visibility of the widget, or if it's a layout, toggle all its items."""
        widget = item.widget()
        if widget:
            widget.setVisible(show)
        else:
            layout = item.layout()
            if layout:
                for i in range(layout.count()):
                    self.recursively_toggle_visibility(layout.itemAt(i), show)

