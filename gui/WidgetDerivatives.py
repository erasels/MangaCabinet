import re

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QComboBox, QCompleter, QTextEdit, QVBoxLayout, QWidget, QLineEdit, QListWidget, QLabel, \
    QListWidgetItem, QGridLayout, QScrollArea, QPushButton, QInputDialog, QListView


class RightClickableComboBox(QComboBox):
    rightClicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        super(RightClickableComboBox, self).mousePressEvent(event)


class CustomListView(QListView):
    middleClicked = pyqtSignal(QtCore.QModelIndex)
    rightClicked = pyqtSignal(QtCore.QModelIndex)

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def mousePressEvent(self, event):
        # Check if middle mouse button was clicked
        btn = event.button()
        if btn == Qt.MidButton or btn == Qt.RightButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                if btn == Qt.RightButton:
                    self.rightClicked.emit(index)
                elif btn == Qt.MidButton:
                    self.middleClicked.emit(index)
        super().mousePressEvent(event)


class CommaCompleter(QCompleter):
    def pathFromIndex(self, index):
        # Current completion
        completion = super().pathFromIndex(index)

        # Text till the current cursor position
        text_till_cursor = self.widget().text()[:self.widget().cursorPosition()]

        # Split based on comma followed by any amount of whitespace
        split_text = re.split(r',\s*', text_till_cursor)

        # Return everything before the last part + the current completion
        return ', '.join(split_text[:-1] + [completion])

    def splitPath(self, path):
        # Return the part after the last comma (with any amount of whitespace)
        return [re.split(r',\s*', path)[-1].strip()]


class CustomTextEdit(QTextEdit):
    contentEdited = pyqtSignal()

    def __init__(self, parent=None):
        super(CustomTextEdit, self).__init__(parent)

    def focusOutEvent(self, event):
        # Call the original focusOutEvent first
        super(CustomTextEdit, self).focusOutEvent(event)

        # Emit the custom signal
        self.contentEdited.emit()


class IdMatcher(QWidget):
    SELECTED_COLOR = QColor(26, 122, 39)
    saveSignal = pyqtSignal()

    def __init__(self, mw, parent=None):
        super(IdMatcher, self).__init__(parent)

        self.mw = mw
        self.selected_items = []
        # Id of entry to not show self
        self.base_id = None
        self.default_bg_col = Qt.transparent

        self.layout = QVBoxLayout(self)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Enter ID or title")
        self.search_input.setStyleSheet(self.mw.styles.get("lineedit"))
        self.search_input.textChanged.connect(lambda: self.update_list())

        self.list_widget = QListWidget(self)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setMaximumHeight(125)
        self.list_widget.itemClicked.connect(self.handle_item_click)

        self.layout.addWidget(QLabel("Similar:"))
        self.layout.addWidget(self.search_input)
        self.layout.addWidget(self.list_widget)

        self.populate_list()

    def emit_save_signal(self):
        self.saveSignal.emit()

    def populate_list(self):
        """Populate the list widget based on the mw data."""
        for entry in self.mw.data:
            item = QListWidgetItem(f"{entry.id} - {entry.display_title()}")

            # Set custom data on the item
            item.setData(Qt.UserRole, entry.id)

            self.list_widget.addItem(item)

    def update_list(self):
        """Filter the list based on the input ID."""
        input = self.search_input.text().strip().lower()
        # Skip filtering for first 2 letters but reset on clearing
        if input and len(input) < 3:
            return

        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            entry_id = item.data(Qt.UserRole)

            if entry_id != self.base_id and (not input or input in item.text().lower()):
                item.setHidden(False)
            else:
                item.setHidden(True)

    def handle_item_click(self, item):
        entry_id = item.data(Qt.UserRole)
        if entry_id in self.selected_items:
            # If already selected, deselect it
            item.setBackground(self.default_bg_col)
            self.selected_items.remove(entry_id)
        else:
            self.selected_items.append(entry_id)
            item.setBackground(IdMatcher.SELECTED_COLOR)

        self.emit_save_signal()

    # Handles resetting and loading the data
    def load(self, entry):
        self.search_input.clear()
        self.selected_items.clear()
        self.selected_items = [sim for sim in entry.similar]
        self.base_id = entry.id

        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            entry_id = item.data(Qt.UserRole)
            if entry_id == self.base_id:
                item.setHidden(True)
            else:
                item.setHidden(False)

            if entry_id in self.selected_items:
                item.setBackground(IdMatcher.SELECTED_COLOR)
            else:
                item.setBackground(self.default_bg_col)


class TagsWidget(QWidget):
    saveSignal = pyqtSignal()

    def __init__(self, mw, parent=None):
        super(TagsWidget, self).__init__(parent)

        self.mw = mw
        self.current_row, self.current_col = 0, 0

        self.tags_widget = QWidget(self)
        self.tags_layout = QGridLayout(self.tags_widget)
        self.tags_layout.setAlignment(Qt.AlignTop)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(self.tags_widget)
        self.scroll_area.setWidgetResizable(True)

        self.add_tag_btn = QPushButton("Add Tag", self)
        self.add_tag_btn.clicked.connect(self.add_new_tag)
        self.add_tag_btn.setStyleSheet(self.mw.styles.get("textbutton"))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tags:"))
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.add_tag_btn)

    def emit_save_signal(self):
        self.saveSignal.emit()

    def add_tag_to_layout(self, tag_name, row, col):
        # Create the QPushButton with both the tag name and the '❌' symbol
        tag_btn = QPushButton(f"❌ {tag_name}")
        tag_btn.setStyleSheet(self.mw.styles.get("tagbutton"))
        tag_btn.setObjectName("Unclicked")  # This allows us to use custom selectors
        tag_btn.clicked.connect(lambda: self.tag_clicked(tag_btn, tag_name))
        tag_btn.setProperty("greyed_out", False)

        # Add the button to the layout
        self.tags_layout.addWidget(tag_btn, row, col)

        # Update the current_row and current_col values
        self.current_col += 1
        if self.current_col > 1:
            self.current_col = 0
            self.current_row += 1

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

        self.emit_save_signal()

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
            self.mw.all_tags.append(text)

            # Check for duplicate tags
            existing_tags = self.extract_tags_from_layout()
            if text not in existing_tags:
                self.add_tag_to_layout(text, self.current_row, self.current_col)
                self.emit_save_signal()

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
