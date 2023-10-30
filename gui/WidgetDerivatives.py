import re

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QComboBox, QCompleter, QTextEdit, QVBoxLayout, QWidget, QLineEdit, QListWidget, QLabel, \
    QListWidgetItem


class RightClickableComboBox(QComboBox):
    rightClicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        super(RightClickableComboBox, self).mousePressEvent(event)


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
    # Declare the custom signal
    contentEdited = pyqtSignal()

    def __init__(self, parent=None):
        super(CustomTextEdit, self).__init__(parent)

    def focusOutEvent(self, event):
        # Call the original focusOutEvent first
        super(CustomTextEdit, self).focusOutEvent(event)

        # Emit the custom signal
        self.contentEdited.emit()


class IdMatcher(QWidget):
    DESELECT_COLOR = QColor(26, 122, 39)
    saveSignal = pyqtSignal()

    def __init__(self, mw, parent=None):
        super(IdMatcher, self).__init__(parent)

        self.mw = mw
        self.selected_items = []
        # Id of entry to not show self
        self.base_id = None
        self.default_bg_col = None

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
        self.default_bg_col = QListWidgetItem("test_item").background().color()
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
            item.setBackground(IdMatcher.DESELECT_COLOR)

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
                item.setBackground(IdMatcher.DESELECT_COLOR)
            else:
                item.setBackground(self.default_bg_col)
