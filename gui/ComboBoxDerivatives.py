from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QComboBox


class CustomComboBox(QComboBox):
    rightClicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        super(CustomComboBox, self).mousePressEvent(event)