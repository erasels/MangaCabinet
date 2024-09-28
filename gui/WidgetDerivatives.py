import json
import os
import re

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, Qt, QRectF, QPointF, QPoint, pyqtSlot, QTimer, QPropertyAnimation
from PyQt5.QtGui import QColor, QPainter, QPixmap, QWheelEvent, QMouseEvent, QShowEvent, QHideEvent, QCursor
from PyQt5.QtWidgets import QComboBox, QCompleter, QTextEdit, QVBoxLayout, QWidget, QLineEdit, QListWidget, QLabel, \
    QListWidgetItem, QGridLayout, QScrollArea, QPushButton, QInputDialog, QListView, QGraphicsView, QGraphicsScene, \
    QHBoxLayout, QGraphicsDropShadowEffect, QMenu, QAction, QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QStyledItemDelegate

import gui
from auxillary.DataAccess import MangaEntry
from gui.Options import bind_dview, show_removed


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
    itemMiddleClicked = pyqtSignal(object)

    def __init__(self, parent=None):
        super(CustomListWidget, self).__init__(parent)
        self.setUniformItemSizes(True)

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            self.itemRightClicked.emit(item)

    def mousePressEvent(self, event):
        super(CustomListWidget, self).mousePressEvent(event)
        if event.button() == Qt.MiddleButton:
            item = self.itemAt(event.pos())
            if item:
                self.itemMiddleClicked.emit(item)


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
        self.label.setWordWrap(True)

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
    def show_notification(self, message, background_color='#6a4a4a', text_color='#FFF', display_time=3000):
        # Stop any existing animation and timer
        self.animation.stop()
        self.timer.stop()
        self.timer.setInterval(display_time)

        self.label.setText(message)
        self.label.setStyleSheet(
            f"QLabel {{ background-color: {background_color}; color: {text_color}; border-radius: 10px; padding: 10px; }}")

        self.adjustSize()  # Adjust the size based on content
        self.setFixedSize(250, max(100, self.height()))  # Ensure minimum height of 100

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
        self.list_widget.itemMiddleClicked.connect(lambda index: self.mw.open_detail_view(index.data(Qt.UserRole)))
        self.mw.dataUpdated.connect(self.add_new_data_to_list)

        self.layout.addWidget(QLabel("Similar:"))
        self.layout.addLayout(input_layout)
        self.layout.addWidget(self.list_widget)

        self.populate_list()

    def populate_list(self):
        """Populate the list widget based on the mw data."""
        for entry in self.mw.data:
            item = self.create_list_item(entry)
            self.list_widget.addItem(item)
            item.setHidden(True)

    def add_new_data_to_list(self, newData: list[MangaEntry]):
        for entry in reversed(newData):
            item = self.create_list_item(entry)
            self.list_widget.insertItem(0, item)
            item.setHidden(True)

        self.update_list()

    def create_list_item(self, entry: MangaEntry):
        item = QListWidgetItem(f"{entry.id} - {entry.display_title()}")

        # Set custom data on the item
        item.setData(Qt.UserRole, entry)

        tooltip_lines = [f"<b>ID:</b> {entry.id}", f"<b>Title:</b> {entry.display_title()}"]

        # Conditional tooltip content
        if entry.description:
            tooltip_lines.append(f"<b>Description:</b> {entry.description}")
        tooltip_lines.append(f"<b>Tags:</b> {', '.join(entry.tags)}")
        if entry.artist and entry.artist != ['']:
            tooltip_lines.append(f"<b>Artist(s):</b> {', '.join(entry.artist)}")

        # Join the tooltip lines with a line break
        tooltip_text = "<br>".join(tooltip_lines)

        # Set the tooltip
        item.setToolTip(tooltip_text)

        return item

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

        self.saveSignal.emit()

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
            entry = item.data(Qt.UserRole)
            entry_id = entry.id

            if not self.mw.settings[show_removed] and entry.removed:
                is_hidden = True
            else:
                # Determine if the item should be hidden
                if self.show_similar_toggle:
                    is_hidden = entry_id not in self.selected_items or entry_id == self.base_id
                else:
                    is_hidden = entry_id == self.base_id or (
                                len(input_filter) > 0 and input_filter.lower() not in item.text().lower())

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
        completer = CommaCompleter(self.mw.tag_data.sorted_keys(), dialog)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        line_edit.setCompleter(completer)

        ok = dialog.exec_()
        text = dialog.textValue()

        if ok and text:
            tags = [tag.strip() for tag in text.split(",")]
            # Check for duplicate tags
            existing_tags = self.extract_tags_from_layout()
            modified = False
            for tag in tags:
                if tag and tag not in existing_tags:
                    self.add_tag_to_layout(tag, self.current_row, self.current_col)
                    modified = True
            if modified:
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
            self.on_right_click()
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

    def on_right_click(self):
        # Check if an entry is loaded
        if not self.entry_id:
            return
        mw = self.thumb_manager.mw  # This is hacky, mw should be easier to access

        context_menu = QMenu(self)
        entry = mw.get_entry_from_id(self.entry_id)

        # Actions
        if not isinstance(self.parent(), gui.DetailView.DetailViewHandler):
            open_detail_action = QAction('Details', self)
            open_detail_action.triggered.connect(lambda: mw.open_detail_view(entry))
            context_menu.addAction(open_detail_action)

        # Only show open in browser if browser is selected and default URL or open_url is set
        if not mw.browser_handler.unsupported and (mw.default_URL or entry.open_url):
            open_browser_action = QAction('Open in Browser', self)
            open_browser_action.triggered.connect(lambda: mw.open_tab_from_entry(entry))
            context_menu.addAction(open_browser_action)

        if entry.disk_location(loose_check=True):
            open_on_disk_action = QAction('Open on System', self)
            open_on_disk_action.triggered.connect(lambda: mw.disk_handler.open(entry))
            context_menu.addAction(open_on_disk_action)

        copy_id_action = QAction('Copy ID', self)
        copy_id_action.triggered.connect(lambda: mw.manga_list_handler.copy_id_to_clipboard(entry.id))
        context_menu.addAction(copy_id_action)

        locate_action = QAction('Locate on Disk', self)
        locate_action.triggered.connect(lambda: mw.manga_list_handler.locate_on_disk(entry))
        context_menu.addAction(locate_action)

        if entry.removed:
            remove_name = 'Revert Removal'
        else:
            remove_name = 'Mark Removed'
        remove_action = QAction(remove_name, self)
        remove_action.triggered.connect(lambda: self.mw.manga_list_handler.update_removed_status(entry))
        # TODO: Streamline save system
        context_menu.addAction(remove_action)

        # Execute the context menu at the cursor's position
        context_menu.exec_(QCursor.pos())


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


class CompleterDelegate(QStyledItemDelegate):
    def __init__(self, completer, parent=None):
        super().__init__(parent)
        self.completer = completer

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setCompleter(self.completer)
        return editor


class DictEditor(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.cur_data = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Table widget for key-value pairs
        self.table = QTableWidget()
        self.table.setStyleSheet(self.mw.styles.get("table"))
        self.table.setColumnCount(3)
        # Set the headers with tooltips
        key_header = QTableWidgetItem("Property")
        key_header.setToolTip("The dictionary key")
        value_header = QTableWidgetItem("Value")
        value_header.setToolTip("The corresponding value (editable)")
        type_header = QTableWidgetItem("Value Type")
        type_header.setToolTip("Type of the value (e.g., int, str, list)")
        self.table.setHorizontalHeaderItem(0, key_header)
        self.table.setHorizontalHeaderItem(1, value_header)
        self.table.setHorizontalHeaderItem(2, type_header)

        # Set the resizing behavior
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Key column resizes based on content
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Value column stretches to fill remaining space
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Value Type column resizes based on content

        completer = QCompleter(list(MangaEntry.ATTRIBUTE_MAP.keys()))
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)

        # Set the delegate with completer for the 'Key' column
        delegate = CompleterDelegate(completer, self.table)
        self.table.setItemDelegateForColumn(0, delegate)

        layout.addWidget(self.table)

        # Add buttons to add and remove rows
        button_layout = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Row")
        self.add_row_btn.setStyleSheet(self.mw.styles.get("textbutton"))
        self.add_row_btn.clicked.connect(self.add_row)
        self.remove_row_btn = QPushButton("Remove Selected Row")
        self.remove_row_btn.setToolTip("You need to select a row by clicking on its row number.")
        self.remove_row_btn.setStyleSheet(self.mw.styles.get("textbutton"))
        self.remove_row_btn.clicked.connect(self.remove_selected_row)

        button_layout.addWidget(self.add_row_btn)
        button_layout.addWidget(self.remove_row_btn)

        layout.addLayout(button_layout)

        # Set the layout and window
        self.setLayout(layout)
        self.setWindowTitle("Dictionary Editor")

    def convert_into_rows(self):
        """Loads the dictionary data into the table."""
        if self.cur_data:
            for key, value in self.cur_data.items():
                self.add_row(key, value, False)

    def add_row(self, key="", value="", manual=True):
        """Adds a new row to the table, with optional initial key and value."""
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)

        # Add key
        key_item = QTableWidgetItem(key)
        self.table.setItem(row_position, 0, key_item)

        # Handle lists by joining them into a comma-separated string
        if isinstance(value, list):
            value_str = ', '.join(map(str, value))  # Convert list elements to string and join
        else:
            value_str = str(value)  # Convert non-list values to string

        # Add value as string
        value_item = QTableWidgetItem(value_str)
        self.table.setItem(row_position, 1, value_item)

        # Add value type combo box
        value_type = self.detect_value_type(value)
        type_combo = QComboBox()
        type_combo.addItems(["str", "int", "float", "bool", "list", "dict"])
        if value_type:
            type_combo.setCurrentText(value_type)
        self.table.setCellWidget(row_position, 2, type_combo)

        if manual:
            self.table.setCurrentCell(row_position, 0)  # Focus the first cell (key column)

    def detect_value_type(self, value):
        """Attempts to detect the type of the value and returns it as a string."""
        try:
            if isinstance(value, list):
                return "list"
            elif isinstance(value, dict):
                return "dict"
            elif isinstance(value, int):
                return "int"
            elif isinstance(value, float):
                return "float"
            elif isinstance(value, bool):
                return "bool"
            else:
                return "str"
        except:
            return "str"

    def apply_completer_to_key(self, row, column):
        """Applies a QCompleter to the key column (column 0)."""
        if column == 0:  # Only apply the completer to the key column
            completer = QCompleter(MangaEntry.ATTRIBUTE_MAP.keys(), self)
            key_item = self.table.item(row, 0)
            if key_item:
                line_edit = self.table.cellWidget(row, column)
                if isinstance(line_edit, QLineEdit):
                    line_edit.setCompleter(completer)

    def remove_selected_row(self):
        """Removes the selected row from the table."""
        indices = self.table.selectionModel().selectedRows()
        for index in sorted(indices):
            self.table.removeRow(index.row())

    def get_table_data(self):
        """Collects data from the table and returns it as a dictionary."""
        new_data = {}
        for row in range(self.table.rowCount()):
            key_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            type_combo = self.table.cellWidget(row, 2)

            key = key_item.text() if key_item else None
            if key:
                value = value_item.text() if value_item else ""
                value_type = type_combo.currentText() if type_combo else "str"

                # Convert value based on selected type
                try:
                    if value_type == "int":
                        value = int(value)
                    elif value_type == "float":
                        value = float(value)
                    elif value_type == "bool":
                        value = value.lower() == "true"
                    elif value_type == "list":
                        value = [v.strip() for v in value.split(",")]
                    elif value_type == "dict":
                        value = json.loads(value)  # Assuming user enters JSON dict as string
                except ValueError:
                    QMessageBox.critical(self, "Error", f"Invalid value for type {value_type}: {value}")
                    return None

                new_data[key] = value

        return new_data

    def save(self):
        """Updates self.cur_data with the new data from the table. Returns True if saving was successful."""
        new_data = self.get_table_data()
        if new_data is not None:
            try:
                # Update cur_data with the new dictionary
                self.cur_data.clear()
                self.cur_data.update(new_data)
                return True
            except TypeError as ex:
                QMessageBox.critical(self, "Error", f"Data contains non-serializable types: {ex}")
        return False

    def load_new_data(self, new_dict):
        """Loads a new dictionary into the table, clearing the existing data."""
        # Clear the current table
        self.table.setRowCount(0)
        self.cur_data = new_dict

        # Load the new data
        self.convert_into_rows()
