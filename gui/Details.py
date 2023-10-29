import json
import os

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QPalette, QFont, QIcon
from PyQt5.QtWidgets import QTextEdit, QPushButton, QGridLayout, QLineEdit, QLabel, QListWidget, QWidget, QComboBox, \
    QInputDialog, QListWidgetItem, QHBoxLayout, QListView, QScrollArea, QVBoxLayout, QCompleter

from auxillary.DataAccess import MangaEntry
from auxillary.JSONMethods import save_json
from gui.WidgetDerivatives import CommaCompleter, CustomTextEdit


class DetailViewHandler:
    def __init__(self, parent):
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
        self.tags_widget = QWidget(self.mw)
        self.tags_layout = QGridLayout(self.tags_widget)
        self.scroll_area = QScrollArea(self.mw)
        self.scroll_area.setWidget(self.tags_widget)
        self.scroll_area.setWidgetResizable(True)

        self.add_tag_btn = QPushButton("Add Tag", self.mw)
        self.add_tag_btn.clicked.connect(self.add_new_tag)
        self.add_tag_btn.setStyleSheet(self.mw.styles.get("textbutton"))
        self.layout.addWidget(QLabel("Tags:"), 1, 0)
        self.layout.addWidget(self.scroll_area, 1, 1, 1, 1)
        self.layout.addWidget(self.add_tag_btn, 1, 2)

        # Description
        self.description_input = CustomTextEdit(self.mw)
        self.description_input.setMaximumHeight(80)
        self.description_input.setStyleSheet(self.mw.styles.get("textedit"))
        self.description_input.setPlaceholderText("Input description which can be searched")
        self.description_input.contentEdited.connect(self.save_changes)
        self.layout.addWidget(QLabel("Description:"), 2, 0)
        self.layout.addWidget(self.description_input, 2, 1, 1, 3)  # Span over three columns

        # Language and Artist
        self.language_input = QLineEdit(self.mw)
        self.artist_input = QLineEdit(self.mw)
        self.language_input.setStyleSheet(self.mw.styles.get("lineedit"))
        self.language_input.setPlaceholderText("Input languages here (seperated by comma)")
        self.language_input.editingFinished.connect(self.save_changes)

        self.artist_input.setStyleSheet(self.mw.styles.get("lineedit"))
        self.artist_input.setPlaceholderText("Input artists/groups here (seperated by comma)")
        self.artist_input.editingFinished.connect(self.save_changes)

        self.layout.addWidget(QLabel("Languages:"), 3, 0)
        self.layout.addWidget(self.language_input, 3, 1)
        self.layout.addWidget(QLabel("Artists:"), 3, 2)
        self.layout.addWidget(self.artist_input, 3, 3)

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

        self.layout.addWidget(QLabel("Score:"), 4, 0)
        self.layout.addWidget(self.score_widget, 4, 1)

        # Group
        self.group_combobox = QComboBox(self.mw)
        self.group_combobox.setStyleSheet(self.mw.styles.get("dropdown"))
        self.group_combobox.currentIndexChanged.connect(self.save_changes)
        self.layout.addWidget(QLabel("Group:"), 4, 2)
        self.layout.addWidget(self.group_combobox, 4, 3)

        # Similar
        self.similar_input = QLineEdit(self.mw)
        completer = CommaCompleter(self.mw.all_ids, self.similar_input)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.similar_input.setCompleter(completer)
        self.similar_input.setPlaceholderText("Enter ids of similar works (seperated by comma)")
        self.similar_input.setStyleSheet(self.mw.styles.get("lineedit"))
        self.similar_input.editingFinished.connect(self.save_changes)
        self.layout.addWidget(QLabel("Similar:"), 5, 0)
        self.layout.addWidget(self.similar_input, 5, 1, 1, 3)

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
        x_position = self.mw.width() - button_width
        y_position = self.mw.height() - button_height
        self.toggle_button.setGeometry(x_position, y_position, button_width, button_height)

    def display_detail(self, index, reload=False):
        if not reload:
            self.cur_data = index.data(Qt.UserRole)
        if not self.cur_data:
            return

        if self.json_edit_mode:
            self.detail_view.setText(json.dumps(self.cur_data, indent=4))
        else:
            # Populate fields with manga data
            self.title_input.setText(self.cur_data.title)
            self.short_title_input.setText(self.cur_data.title_short)

            self.load_tags(self.cur_data.tags)

            self.description_input.setText(self.cur_data.description)
            self.language_input.setText(", ".join(self.cur_data.language))
            self.artist_input.setText(", ".join(self.cur_data.artist))

            self.set_score(self.cur_data.score, saveChange=False)

            self.similar_input.setText(", ".join(map(str, self.cur_data.similar)))

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
                    print(f"{self.cur_data.id}: {attr} was updated with:\n{new_value}")
                    data_changed = True

            attributes_mapping = {
                'title': self.title_input.text,
                'title_short': self.short_title_input.text,
                'tags': self.extract_tags_from_layout,
                'description': self.description_input.toPlainText,
                'language': lambda: [lang.strip() for lang in self.language_input.text().split(",")],
                'artist': lambda: [artist.strip() for artist in self.artist_input.text().split(",")],
                'score': self.get_current_score,
                'similar': lambda: [int(id_str.strip()) for id_str in self.similar_input.text().split(",") if
                                    self.similar_input.text()]
            }

            for attr, func in attributes_mapping.items():
                update_attribute(attr, func())

            # Special case for the group combobox
            group_value = self.group_combobox.currentText()
            if group_value == "None":
                if self.cur_data.group:
                    delattr(self.cur_data, 'group')
                    data_changed = True
            else:
                update_attribute('group', group_value)

            if data_changed:
                self.mw.is_data_modified = True
                self.mw.search_bar_handler.update_list()

    def add_tag_to_layout(self, tag_name, row, col):
        # Create the QPushButton with both the tag name and the '❌' symbol
        tag_btn = QPushButton(f"❌ {tag_name}")
        tag_btn.setStyleSheet(self.mw.styles.get("tagbutton"))
        tag_btn.setObjectName("Unclicked")  # This allows us to use custom selectors
        tag_btn.clicked.connect(lambda: self.tag_clicked(tag_btn, tag_name))
        tag_btn.setProperty("greyed_out", False)

        # Add the button to the layout
        self.tags_layout.addWidget(tag_btn, row, col)

    def tag_clicked(self, tag_btn, original_text):
        # Handles graying out which will be used by save_changes to remove it later on
        if tag_btn.property("greyed_out"):
            tag_btn.setObjectName("Unclicked")
            tag_btn.setProperty("greyed_out", False)
        else:
            tag_btn.setObjectName("Clicked")
            tag_btn.setProperty("greyed_out", True)
        # Refresh style after changing the object name
        tag_btn.style().unpolish(tag_btn)
        tag_btn.style().polish(tag_btn)

        self.save_changes()

    def add_new_tag(self):
        # Create a QInputDialog
        dialog = QInputDialog(self.mw)
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.setWindowTitle('Add Tag')
        dialog.setLabelText('Enter new tag:')
        dialog.setStyleSheet(self.mw.styles["lineedit"] + "\n" + self.mw.styles["textbutton"])

        line_edit = dialog.findChild(QLineEdit)
        completer = QCompleter(list(self.mw.all_tags), dialog)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        line_edit.setCompleter(completer)

        ok = dialog.exec_()
        text = dialog.textValue()

        if ok and text:
            text = text.strip()
            # Update all tags in case it's a new one
            self.mw.all_tags.add(text)

            # Check for duplicate tags
            existing_tags = self.extract_tags_from_layout()
            if text not in existing_tags:
                self.add_tag_to_layout(text, self.current_row, self.current_col)
                self.save_changes()

    def extract_tags_from_layout(self):
        tags = []
        for i in range(self.tags_layout.count()):
            widget = self.tags_layout.itemAt(i).widget()
            if isinstance(widget, QPushButton):
                is_greyed_out = widget.property("greyed_out")
                # If the button isn't greyed out, extract its tag text
                if not is_greyed_out:
                    tag_text = widget.text().replace("❌ ", "")
                    tags.append(tag_text)
        return tags

    def load_tags(self, tags_list):
        self.clear_tags_layout()
        self.current_row, self.current_col = 0, 0
        for tag in tags_list:
            self.add_tag_to_layout(tag, self.current_row, self.current_col)
            # Update the current_row and current_col values
            self.current_col += 1
            if self.current_col > 1:
                self.current_col = 0
                self.current_row += 1

    def clear_tags_layout(self):
        self.current_row = 0
        self.current_col = 0
        for i in reversed(range(self.tags_layout.count())):
            widget = self.tags_layout.itemAt(i).widget()
            if widget is not None:
                # Remove the widget from layout
                self.tags_layout.removeWidget(widget)
                # Destroy the widget (this will also remove it from the screen)
                widget.deleteLater()

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

