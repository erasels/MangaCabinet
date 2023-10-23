from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QComboBox


class RightClickableComboBox(QComboBox):
    rightClicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        super(RightClickableComboBox, self).mousePressEvent(event)