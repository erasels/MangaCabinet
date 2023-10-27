import re

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QComboBox, QCompleter, QTextEdit


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