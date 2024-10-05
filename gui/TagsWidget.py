from PyQt5.QtCore import pyqtSignal, Qt, QRect, QSize, QPoint
from PyQt5.QtWidgets import QWidget, QScrollArea, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QInputDialog, QLineEdit, QLayout, QSizePolicy

from gui.WidgetDerivatives import CommaCompleter


class TagsWidget(QWidget):
    saveSignal = pyqtSignal()

    def __init__(self, mw, parent=None):
        super(TagsWidget, self).__init__(parent)

        self.mw = mw
        self.loaded = False

        # Create flow layout
        self.tags_widget = QWidget(self)
        self.tags_layout = FlowLayout(self.tags_widget, spacing=3)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(self.tags_widget)
        self.scroll_area.setWidgetResizable(True)

        buttons_layout = QHBoxLayout()
        self.add_tag_btn = QPushButton("Add Tag", self)
        self.add_tag_btn.clicked.connect(self.add_new_tag)
        self.add_tag_btn.setStyleSheet(self.mw.styles.get("textbutton"))
        buttons_layout.addWidget(self.add_tag_btn)

        self.browse_tag_btn = QPushButton("Browse Tags", self)
        self.browse_tag_btn.clicked.connect(self.mw.open_tag_view)
        self.browse_tag_btn.setStyleSheet(self.mw.styles.get("textbutton"))
        buttons_layout.addWidget(self.browse_tag_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Tags: (Right-click to highlight)"))
        layout.addWidget(self.scroll_area)
        layout.addLayout(buttons_layout)

    def signal_save(self):
        self.saveSignal.emit()

    def add_tag_to_layout(self, tag_name, special=False):
        tag_btn = TagButton(tag_name, special, self.mw)
        tag_btn.update_style()
        tag_btn.toggledGreyedOut.connect(self.signal_save)
        tag_btn.toggledSpecial.connect(self.signal_save)
        self.tags_layout.addWidget(tag_btn)

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

        self.signal_save()

    def add_new_tag(self):
        if not self.loaded:
            return
        # Create a QInputDialog
        dialog = QInputDialog(self.mw)
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.setWindowTitle('Add Tag')
        dialog.setLabelText('Enter new tag:')
        dialog.setStyleSheet(self.mw.styles["lineedit"] + "\n" + self.mw.styles["textbutton"])

        line_edit = dialog.findChild(QLineEdit)
        completer = CommaCompleter(self.mw.tag_data.sorted_keys(), dialog)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        line_edit.setCompleter(completer)

        ok = dialog.exec_()
        text = dialog.textValue()

        if ok and text:
            tags = [tag.strip() for tag in text.split(",")]
            # Check for duplicate tags
            existing_tags = self.extract_tagdata_from_layout()[0]
            modified = False
            for tag in tags:
                if tag and tag not in existing_tags:
                    self.add_tag_to_layout(tag)
                    modified = True
            if modified:
                self.signal_save()

    def extract_tagdata_from_layout(self):
        tags = []
        special_tags = []
        for i in range(self.tags_layout.count()):
            widget = self.tags_layout.itemAt(i).widget()
            if isinstance(widget, TagButton):
                tag_text = widget.tag_name
                if not widget.property("greyed_out"):
                    tags.append(tag_text)
                if widget.property("special"):
                    special_tags.append(tag_text)
        return tags, special_tags

    def load_tags(self, entry):
        self.loaded = True
        self.clear_tags_layout()
        for tag in entry.tags:
            special = tag in entry.highlighted_tags
            self.add_tag_to_layout(tag, special=special)

    def clear_tags_layout(self):
        for i in reversed(range(self.tags_layout.count())):
            widget = self.tags_layout.itemAt(i).widget()
            if widget is not None:
                self.tags_layout.removeWidget(widget)
                # Destroy the widget (this will also remove it from the screen)
                widget.deleteLater()


class FlowLayout(QLayout):
    """
    Special layout that allows adding items of different sizes to it and fits as many items into
    a row as there is space before moving going to the next.
    """
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

        self.itemList = []

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().left(), 2 * self.contentsMargins().top())
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing() + item.widget().style().layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
            )
            spaceY = self.spacing() + item.widget().style().layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
            )

            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()


class TagButton(QPushButton):
    """
    The buttons used in the tag widget that represent tags. Allows for custom logic regarding
    left-click/right-click logic.
    """
    toggledSpecial = pyqtSignal()
    toggledGreyedOut = pyqtSignal()

    def __init__(self, tag_name, isSpecial, mw):
        super().__init__(f"❌{tag_name}")
        self.tag_name = tag_name
        self.mw = mw
        self.setStyleSheet(self.mw.styles.get("tagbutton"))
        self.setObjectName("Unclicked")  # For styling
        self.setProperty("greyed_out", False)
        self.setProperty("special", False)
        if isSpecial:
            self.toggle_special(False)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            if not self.property("greyed_out"):  # Only allow right-click if not greyed out
                self.toggle_special()
        elif event.button() == Qt.LeftButton:
            if not self.property("special"):  # Left-click only affects non-special tags
                self.toggle_greyed_out()
        else:
            super().mousePressEvent(event)

    def toggle_greyed_out(self):
        if self.property("greyed_out"):
            self.setObjectName("Unclicked")
            self.setProperty("greyed_out", False)
        else:
            self.setObjectName("Clicked")
            self.setProperty("greyed_out", True)
        self.update_style()
        self.toggledGreyedOut.emit()

    def toggle_special(self, shouldEmit=True):
        special = not self.property("special")
        self.setProperty("special", special)
        # Update the text to remove or re-add the "❌"
        if special:
            self.setText(self.tag_name)
        else:
            self.setText(f"❌{self.tag_name}")
        self.update_style()
        if shouldEmit:
            self.toggledSpecial.emit()

    def update_style(self):
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
