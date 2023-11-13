import os
import re

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, Qt, QRectF, QPointF, QPoint, pyqtSlot, QTimer, QPropertyAnimation
from PyQt5.QtGui import QColor, QPainter, QPixmap, QWheelEvent, QMouseEvent, QShowEvent, QHideEvent
from PyQt5.QtWidgets import QComboBox, QCompleter, QTextEdit, QVBoxLayout, QWidget, QLineEdit, QListWidget, QLabel, \
    QListWidgetItem, QGridLayout, QScrollArea, QPushButton, QInputDialog, QListView, QGraphicsView, QGraphicsScene, \
    QHBoxLayout, QGraphicsDropShadowEffect

from gui.Options import bind_dview


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
        self.setUniformItemSizes(True)

    def mousePressEvent(self, event):
        # Check if other mouse button was clicked
        btn = event.button()
        if btn == Qt.MidButton or btn == Qt.RightButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                if btn == Qt.RightButton:
                    self.rightClicked.emit(index)
                elif btn == Qt.MidButton:
                    self.middleClicked.emit(index)
        else:
            super().mousePressEvent(event)


class CustomListWidget(QListWidget):
    itemRightClicked = pyqtSignal(object)

    def __init__(self, parent=None):
        super(CustomListWidget, self).__init__(parent)
        self.setUniformItemSizes(True)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            self.itemRightClicked.emit(item)


class DraggableListWidget(QListWidget):
    itemMoved = pyqtSignal(int, int)  # Signal to emit when item is moved

    def dropEvent(self, event):
        """ Reimplemented to emit the itemMoved signal """
        before_drop_row = self.currentRow()
        super().dropEvent(event)
        after_drop_row = self.currentRow()
        self.itemMoved.emit(before_drop_row, after_drop_row)


class CommaCompleter(QCompleter):
    def pathFromIndex(self, index):
        completion = super().pathFromIndex(index)
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


class ToastNotification(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(250, 100)

        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignCenter)

        # Apply drop shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(2)
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        # Animation
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(500)
        self.timer = QTimer()
        self.timer.setInterval(3000)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_notification)

    @pyqtSlot()
    def show_notification(self, message, background_color='#6a4a4a', text_color='#FFF'):
        # Stop any existing animation and timer
        self.animation.stop()
        self.timer.stop()

        self.label.setText(message)
        self.label.setStyleSheet(
            f"QLabel {{ background-color: {background_color}; color: {text_color}; border-radius: 10px; padding: 10px; }}")

        parent_geometry = self.parent().geometry()
        right = parent_geometry.right() - self.width() - 20
        bottom = parent_geometry.bottom() - self.height() - 20

        # Position the notification in the bottom-right corner of the parent's geometry
        self.move(right, bottom)
        self.show()

        # Start animation
        self.animation.setStartValue(QPoint(self.x(), bottom))
        self.animation.setEndValue(QPoint(self.x(), bottom - self.height() - 20))
        self.animation.start()

        # Start timer to auto-hide notification
        self.timer.start()

    @pyqtSlot()
    def hide_notification(self):
        self.timer.stop()

        bottom = self.parent().geometry().bottom() - self.height() - 20
        # Slide out animation
        self.animation.setStartValue(QPoint(self.x(), bottom - self.height() - 20))
        self.animation.setEndValue(QPoint(self.x(), bottom + 20))
        self.animation.finished.connect(self.finish_anim)  # Ensure widget is closed after animation
        self.animation.start()

    def finish_anim(self):
        self.close()
        self.animation.finished.disconnect()


class IdMatcher(QWidget):
    SELECTED_COLOR = QColor(26, 122, 39)
    DEFAULT_COLOR = Qt.transparent
    saveSignal = pyqtSignal()
    DEFAULT_RATIO = 0.65

    def __init__(self, mw, parent=None):
        super(IdMatcher, self).__init__(parent)

        self.mw = mw
        self.selected_items = []
        # Id of entry to not show self
        self.base_id = None
        self.show_similar_toggle = False

        self.layout = QVBoxLayout(self)

        input_layout = QHBoxLayout()
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Enter ID or title")
        self.search_input.setStyleSheet(self.mw.styles.get("lineedit"))
        self.search_input.textChanged.connect(lambda: self.update_list())
        input_layout.addWidget(self.search_input, 1)

        self.toggle_button = QPushButton("Show Similar", self)
        self.toggle_button.setStyleSheet(self.mw.styles.get("textbutton"))
        self.toggle_button.clicked.connect(self.toggle_similar_items)
        input_layout.addWidget(self.toggle_button)

        self.list_widget = CustomListWidget(self)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.itemClicked.connect(self.handle_item_click)
        self.list_widget.itemRightClicked.connect(lambda index: self.mw.open_detail_view(index.data(Qt.UserRole)))

        self.layout.addWidget(QLabel("Similar:"))
        self.layout.addLayout(input_layout)
        self.layout.addWidget(self.list_widget)

        self.populate_list()

    def emit_save_signal(self):
        self.saveSignal.emit()

    def populate_list(self):
        """Populate the list widget based on the mw data."""
        for entry in self.mw.data:
            item = QListWidgetItem(f"{entry.id} - {entry.display_title()}")

            # Set custom data on the item
            item.setData(Qt.UserRole, entry)

            tooltip_lines = []

            # Conditional tooltip content
            tooltip_lines.append(f"<b>ID:</b> {entry.id}")
            tooltip_lines.append(f"<b>Title:</b> {entry.display_title()}")
            if entry.description:
                tooltip_lines.append(f"<b>Description:</b> {entry.description}")
            tooltip_lines.append(f"<b>Tags:</b> {', '.join(entry.tags)}")
            if entry.artist and entry.artist != ['']:
                tooltip_lines.append(f"<b>Artist(s):</b> {', '.join(entry.artist)}")

            # Join the tooltip lines with a line break
            tooltip_text = "<br>".join(tooltip_lines)

            # Set the tooltip
            item.setToolTip(tooltip_text)

            self.list_widget.addItem(item)
            item.setHidden(True)

    def update_list(self):
        """Filter the list based on the input ID."""
        if not self.base_id:
            return

        input = self.search_input.text().strip().lower()
        # Skip filtering for first 2 letters but reset on clearing
        if input and len(input) < 3:
            return

        self._update_item_visibility_and_color(input_filter=input)

    def toggle_similar_items(self):
        """Toggle the display of similar items in the list."""
        self.show_similar_toggle = not self.show_similar_toggle
        if self.show_similar_toggle:
            self.toggle_button.setText("Show All")
        else:
            self.toggle_button.setText("Show Similar")

        self.update_list()

    def handle_item_click(self, item):
        if not self.base_id:
            return

        entry_id = item.data(Qt.UserRole).id
        if entry_id in self.selected_items:
            # If already selected, deselect it
            item.setBackground(IdMatcher.DEFAULT_COLOR)
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

        self._update_item_visibility_and_color(update_color=True)

    def _update_item_visibility_and_color(self, input_filter="", update_color=False):
        for idx in range(self.list_widget.count()):
            item = self.list_widget.item(idx)
            entry_id = item.data(Qt.UserRole).id

            # Determine if the item should be hidden
            if self.show_similar_toggle:
                is_hidden = entry_id not in self.selected_items or entry_id == self.base_id
            else:
                is_hidden = entry_id == self.base_id or (
                            len(input_filter) > 0 and input_filter not in item.text().lower())

            item.setHidden(is_hidden)

            if update_color:
                if entry_id in self.selected_items:
                    item.setBackground(IdMatcher.SELECTED_COLOR)
                else:
                    item.setBackground(IdMatcher.DEFAULT_COLOR)


class TagsWidget(QWidget):
    saveSignal = pyqtSignal()

    def __init__(self, mw, parent=None):
        super(TagsWidget, self).__init__(parent)

        self.mw = mw
        self.current_row, self.current_col = 0, 0
        self.loaded = False

        self.tags_widget = QWidget(self)
        self.tags_layout = QGridLayout(self.tags_widget)
        self.tags_layout.setAlignment(Qt.AlignTop)

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
        layout.addWidget(QLabel("Tags:"))
        layout.addWidget(self.scroll_area)
        layout.addLayout(buttons_layout)

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
        if not self.loaded:
            return
        # Create a QInputDialog
        dialog = QInputDialog(self.mw)
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.setWindowTitle('Add Tag')
        dialog.setLabelText('Enter new tag:')
        dialog.setStyleSheet(self.mw.styles["lineedit"] + "\n" + self.mw.styles["textbutton"])

        line_edit = dialog.findChild(QLineEdit)
        completer = QCompleter(self.mw.tag_data.sorted_keys(), dialog)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        line_edit.setCompleter(completer)

        ok = dialog.exec_()
        text = dialog.textValue()

        if ok and text:
            text = text.strip()
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
        self.loaded = True
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


class ImageViewer(QGraphicsView):
    rightClicked = pyqtSignal()
    MAX_ZOOM = 4.0

    def __init__(self, thumb_manager, parent=None, dynamic_show=False):
        super(ImageViewer, self).__init__(parent)

        self.thumb_manager = thumb_manager
        self.dynamic_show = dynamic_show
        self.entry_id = None
        self.original_pixmap = None
        self._drag = False
        self._start_drag_pos = QPointF(0, 0)

        # Setup view
        self.image_scene = QGraphicsScene()
        self.setScene(self.image_scene)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setAlignment(Qt.AlignCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._zoom_factor = 1.0

    def load_image(self, entry_id):
        self.entry_id = entry_id
        self._zoom_factor = 1.0
        if not self.isHidden():
            self.original_pixmap = self.thumb_manager.get_thumbnail(entry_id)
            self._update_pixmap()

    def _update_pixmap(self):
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                self.size() * self._zoom_factor,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_scene.clear()
            self.image_scene.addPixmap(scaled_pixmap)
            self.image_scene.setSceneRect(QRectF(scaled_pixmap.rect()))

    def resizeEvent(self, event):
        self._update_pixmap()
        super().resizeEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        elif event.button() == Qt.LeftButton:
            self._drag = True
            self._start_drag_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.MiddleButton:
            self._zoom_factor = 1.0
            self._update_pixmap()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag:
            delta = event.pos() - self._start_drag_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._start_drag_pos = event.pos()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        delta = event.angleDelta().y()
        if delta > 0:  # Zoom in
            factor = 1.25
            self._zoom_factor = min(factor * self._zoom_factor, ImageViewer.MAX_ZOOM)
        elif delta < 0:  # Zoom out
            factor = 0.8
            self._zoom_factor = max(factor * self._zoom_factor, 1.0)
        self._update_pixmap()

        super().wheelEvent(event)

    def showEvent(self, event: QShowEvent):
        if self.dynamic_show:
            if self.shouldShow():
                super().showEvent(event)
            else:
                self.hide()

    def hideEvent(self, event: QHideEvent):
        super().hideEvent(event)

    def shouldShow(self):
        return not self.parent().settings[bind_dview]

    def set_dynamic_show(self, state):
        self.setHidden(state)
        if self.isVisible():
            self.load_image(self.entry_id)


class RatingWidget(QWidget):
    scoreChanged = pyqtSignal(int)

    def __init__(self, parent=None, initial_score=0, max_stars=5):
        super().__init__(parent)
        self.stars = None
        self.max_stars = max_stars
        self.current_score = initial_score
        self.img_empty_star = os.path.join(parent.image_path, 'star_empty.png')
        self.img_star = os.path.join(parent.image_path, 'star.png')
        self.init_ui(initial_score)

    def init_ui(self, initial_score):
        layout = QHBoxLayout(self)
        self.stars = []

        for i in range(self.max_stars):
            star_label = QLabel(self)
            pixmap = QPixmap(self.img_empty_star)
            star_label.setPixmap(pixmap)
            star_label.mousePressEvent = lambda event, i=i: self.set_score(i + 1)
            layout.addWidget(star_label)
            self.stars.append(star_label)

        self.set_score(initial_score, saveChange=False)

    def set_score(self, score, saveChange=True):
        self.current_score = score
        for i, star_label in enumerate(self.stars):
            pixmap = QPixmap(self.img_star if i < score else self.img_empty_star)
            star_label.setPixmap(pixmap)
        if saveChange:
            self.scoreChanged.emit(score)  # Emit the scoreChanged signal

    def get_current_score(self):
        return self.current_score
