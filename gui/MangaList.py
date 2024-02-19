import functools
import logging
import math
import os
import typing
from datetime import datetime

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QRect, QSize, QRectF, QPoint, QObject, pyqtSignal, QThreadPool, pyqtSlot, QTimer
from PyQt5.QtGui import QColor, QPen, QFontMetrics, QPainterPath, QStandardItemModel, QStandardItem, QPixmap, QCursor
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle, QListView, QAbstractItemView, QWidget, QVBoxLayout, \
    QLabel, QGraphicsDropShadowEffect, QMenu, QAction

from gui.Options import thumbnail_preview, thumbnail_delegate, show_removed
from gui.WidgetDerivatives import CustomListView


class ListViewHandler:
    THUMB_SPACING, MANGA_SPACING = 3, 0

    def __init__(self, parent):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.manga_delegate = None
        self.thumb_delegate = None
        self.list_model = None
        self.list_view = None
        self.mw = parent
        self.selection_history = {'back': [], 'forward': []}
        self.current_id = None
        self.init_ui()

    def init_ui(self):
        # List view
        self.list_view = SpecialListView(self.mw)
        self.list_model = QStandardItemModel(self.list_view)
        self.list_view.setModel(self.list_model)

        self.list_view.setWrapping(True)
        self.list_view.setFlow(QListView.LeftToRight)
        self.list_view.setLayoutMode(QListView.Batched)

        self.manga_delegate = MangaDelegate(self.mw, self.list_view)
        self.thumb_delegate = ThumbnailDelegate(self.mw, self.list_view)
        self.switch_delegate(self.mw.settings[thumbnail_delegate])
        # Prevent editing on double-click
        self.list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list_view.clicked.connect(self.mw.details_handler.display_detail)
        # To force manual update because I use custom highlighting logic
        self.list_view.clicked.connect(lambda: self.list_view.viewport().update())
        self.list_view.clicked.connect(self.update_selection_history)
        self.list_view.middleClicked.connect(self.open_tab)
        #self.list_view.rightClicked.connect(lambda index: self.mw.open_detail_view(index.data(Qt.UserRole)))
        self.list_view.rightClicked.connect(self.on_right_click)

    def get_widget(self):
        return self.list_view

    def handle_resize(self):
        self.list_view.updateGeometries()
        self.list_view.doItemsLayout()  # Force the view to relayout items.

    def switch_delegate(self, thumbnail):
        if thumbnail:
            self.list_view.setItemDelegate(self.thumb_delegate)
            self.list_view.setSpacing(self.THUMB_SPACING)
        else:
            self.list_view.setItemDelegate(self.manga_delegate)
            self.list_view.setSpacing(self.MANGA_SPACING)
        self.list_view.viewport().update()

    def clear_view(self):
        self.list_model.clear()

    def add_item(self, entry):
        item = QStandardItem()
        item.setData(entry, Qt.UserRole)
        self.list_model.appendRow(item)

    def add_items(self, entries, clear_list=True):
        if clear_list:
            self.clear_view()
        self.list_model.layoutAboutToBeChanged.emit()
        for entry in entries:
            item = QStandardItem()
            item.setData(entry, Qt.UserRole)
            self.list_model.appendRow(item)
        self.list_model.layoutChanged.emit()

    def update_selection_history(self, index):
        if index.isValid():
            unique_id = index.data(Qt.UserRole).id
            # Push the current_id into the back stack only if it's different from the last entry
            if self.current_id is not None and (
                    not self.selection_history['back'] or self.current_id != self.selection_history['back'][-1]):
                self.selection_history['back'].append(self.current_id)
            self.current_id = unique_id
            self.selection_history['forward'].clear()

    def navigate_back(self):
        if self.selection_history['back']:
            last_id = self.selection_history['back'][-1]
            if last_id != self.current_id and self.select_index_by_id(last_id):
                self.selection_history['forward'].append(self.current_id)
                self.current_id = self.selection_history['back'].pop()

    def navigate_forward(self):
        if self.selection_history['forward']:
            last_id = self.selection_history['forward'][-1]
            if self.select_index_by_id(last_id):
                self.selection_history['back'].append(self.current_id)
                self.current_id = self.selection_history['forward'].pop()

    def select_index_by_id(self, unique_id, notify_on_failure=True):
        """Select an item in the list_view by its Id, does not update selection history and by default notifies on failure"""
        for row in range(self.list_model.rowCount()):
            if self.list_model.item(row).data(Qt.UserRole).id == unique_id:
                self.select_index(self.list_model.index(row, 0))
                return True
        if notify_on_failure:
            entry = self.mw.data[self.mw.entry_to_index[unique_id]]
            if entry:
                self.mw.toast.show_notification(f"{unique_id} is not in the list currently.\n{entry.display_title()}")
        return False

    def select_index(self, index, update_history=False):
        self.list_view.setCurrentIndex(index)
        self.mw.details_handler.display_detail(index)
        if update_history:
            self.update_selection_history(index)

    def rescroll(self):
        current_index = self.list_view.currentIndex()
        if current_index:
            self.list_view.scrollTo(current_index)

    def on_right_click(self, index):
        # Check if the index is valid
        if not index.isValid():
            return

        context_menu = QMenu(self.list_view)

        entry = index.data(Qt.UserRole)

        # Actions
        open_detail_action = QAction('Details', self.list_view)
        open_browser_action = QAction('Open in Browser', self.list_view)
        edit_action = QAction('Edit', self.list_view)
        if entry.removed:
            remove_name = 'Revert Removal'
        else:
            remove_name = 'Mark Removed'
        remove_action = QAction(remove_name, self.list_view)

        # Connect actions to slots or functions
        open_detail_action.triggered.connect(lambda: self.mw.open_detail_view(entry))
        open_browser_action.triggered.connect(lambda: self.open_tab(index))
        edit_action.triggered.connect(lambda: self.select_index(index, True))
        remove_action.triggered.connect(lambda: self.update_removed_status(entry))

        # Add actions to the menu
        context_menu.addAction(open_detail_action)
        context_menu.addAction(open_browser_action)
        context_menu.addAction(edit_action)
        context_menu.addAction(remove_action)

        # Execute the context menu at the cursor's position
        context_menu.exec_(QCursor.pos())

    def update_removed_status(self, entry):
        # TODO: This is a copy of detail view remove, streamline save system
        entry.removed = not entry.removed
        self.mw.is_data_modified = True
        entry.update_last_edited()
        self.logger.debug(f"{entry.id}: removed was updated with: deleted {entry.removed}")

        if not self.mw.settings[show_removed]:
            self.mw.search_bar_handler.update_list()

    def open_tab(self, index):
        entry = index.data(Qt.UserRole)
        if not self.mw.browser_handler.unsupported:
            entry.last_opened = datetime.now().strftime("%Y/%m/%d %H:%M")
            entry.opens += 1
            self.logger.debug(f"{entry.id}: MC_num_opens was updated with: {entry.opens}")
            entry.update_last_opened()
            # entry.update_last_edited()  # Doesn't feel like it should be updated here
            self.mw.is_data_modified = True
            if self.mw.details_handler.json_edit_mode:
                self.mw.details_handler.display_detail(index, True)
        self.mw.browser_handler.open_tab(entry)


def blend_colors(color1, color2, alpha):
    """
    Blend color1 and color2. The alpha parameter defines the proportion of color1.
    alpha = 1.0 will show only color1, alpha = 0.0 will show only color2.
    """
    r1, g1, b1, _ = color1.getRgb()
    r2, g2, b2, _ = color2.getRgb()
    r = r1 * alpha + r2 * (1 - alpha)
    g = g1 * alpha + g2 * (1 - alpha)
    b = b1 * alpha + b2 * (1 - alpha)
    return QColor(int(r), int(g), int(b))


def is_dark_color(color: QColor) -> bool:
    """Return True if the color is considered dark based on luminance."""
    luminance = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    return luminance < 128


def wordwrap(text, width):
    """
    A simple word wrap function that wraps text at a given number of characters.
    """
    return [text[i:i + int(width)] for i in range(0, len(text), int(width))]


# Constants for tags
MAX_TAGS = 6
TAG_WIDTH = 60
TAG_HEIGHT = 20
TAG_SPACING = 3
TAG_COLUMNS = 3
TAG_MINIMUM_FONT_SIZE = 7
TAG_BACKGROUND_COLOR = QColor("#505050")

TITLE_MINIMUM_FONT_SIZE = 7
DEFAULT_ITEM_BG_COLOR = QColor("#2A2A2A")
STAR_DIM_BG_COLOR = QColor("#000000")
DEFAULT_ITEM_OUTLINE_COLOR = QColor("#666666")
HIGHLIGHT_ITEM_OUTLINE_COLOR = QColor("#FFAA00")


class MangaDelegate(QStyledItemDelegate):

    def __init__(self, main_window, parent: typing.Optional[QtCore.QObject] = ...):
        super().__init__(parent)
        self.mw = main_window
        self.img_star = QPixmap(os.path.join(self.mw.image_path, 'star.png'))
        self.img_star = self.img_star.scaled(int(self.img_star.width() * 0.5),
                                             int(self.img_star.height() * 0.5),
                                             Qt.KeepAspectRatio)
        self.base_pen_color = None

    def paint(self, painter, option, index):
        # Retrieve item data from the model
        entry = index.data(Qt.UserRole)

        # Draw the background and border
        painter.save()

        # Reduce background opacity if removed
        if entry.removed:
            painter.setOpacity(0.2)

        if not self.base_pen_color:
            self.base_pen_color = painter.pen().color()

        background_color = DEFAULT_ITEM_BG_COLOR
        outline_thickness = 1
        outline_color = DEFAULT_ITEM_OUTLINE_COLOR

        if self.mw.details_handler.cur_data and self.mw.details_handler.cur_data.id == entry.id:
            background_color = option.palette.highlight().color()
            outline_thickness = 2
            outline_color = HIGHLIGHT_ITEM_OUTLINE_COLOR
        else:
            # Set collection-specific color
            collection_name = entry.collection
            if collection_name and collection_name in self.mw.collection_handler.collections:
                color = self.mw.collection_handler.collections[collection_name].get("color")
                if color:
                    background_color = blend_colors(DEFAULT_ITEM_BG_COLOR, QColor(color), 0.2)

            if option.state & QStyle.State_MouseOver:
                mod_color = QColor(255, 255, 255, 50)  # semi-transparent white to brighten the color
                background_color = blend_colors(background_color, mod_color, 0.8)

        item_path = QPainterPath()
        item_path.addRoundedRect(QRectF(option.rect), 5, 5)
        painter.fillPath(item_path, background_color)
        painter.strokePath(item_path, QPen(outline_color, outline_thickness))
        painter.restore()

        title_rect = option.rect.adjusted(10, 10, -10, -10)

        # Draw score
        score = entry.score
        if score:
            star_spacing = 4  # adjust this based on your preferences
            star_width = self.img_star.width()
            star_height = self.img_star.height()
            total_height_for_stars = score * star_height + (score - 1) * star_spacing

            # Calculating the top-left point to start drawing stars
            start_x = option.rect.x() + 5  # adding 8 pixels padding from left. Adjust as needed.
            start_y = option.rect.y() + 5  # center align vertically

            rect_width = star_width + 8
            rect_height = score * star_height + (score - 1) * star_spacing + 10
            rect_color = blend_colors(background_color, STAR_DIM_BG_COLOR, 0.7)
            painter.save()
            painter.setBrush(rect_color)
            painter.setPen(Qt.NoPen)
            # the 5,5 are the x,y radii of the rounded corners
            painter.drawRoundedRect(QRect(start_x - 4, start_y - 3, rect_width, rect_height), 5, 5)
            painter.restore()

            for i in range(score):
                painter.drawPixmap(start_x, int(start_y + i * (star_height + star_spacing)), self.img_star)

            # Adjust title_rect to avoid overlapping with the stars
            title_rect = title_rect.adjusted(star_width, 0, 0, 0)

        painter.save()

        # Reduce text opacity if removed
        if entry.removed:
            pen = painter.pen()
            color = pen.color()
            color.setAlpha(45)
            pen.setColor(color)
            painter.setPen(pen)

        # Draw the title
        title = entry.display_title()
        tags_total_width = TAG_COLUMNS * TAG_WIDTH + (TAG_COLUMNS - 1) * TAG_SPACING
        title_rect.setWidth(title_rect.width() - tags_total_width)

        font_metrics = QFontMetrics(painter.font())
        original_font = painter.font()

        # Dynamically reduce the title size if it doesn't fit
        font = painter.font()
        while font_metrics.width(title) > title_rect.width() and font.pointSize() > TITLE_MINIMUM_FONT_SIZE:
            font.setPointSize(font.pointSize() - 1)
            painter.setFont(font)
            font_metrics = QFontMetrics(font)

        if font_metrics.width(title) > title_rect.width():
            title = font_metrics.elidedText(title, Qt.ElideRight, title_rect.width())

        # Change text color if background is light
        if not is_dark_color(background_color):
            painter.setPen(Qt.black)

        painter.drawText(title_rect, Qt.AlignLeft, title)

        # Move down for artists
        title_rect.translate(0, font_metrics.height())
        painter.setFont(original_font)

        # Display the artists
        artists = entry.artist
        groups = entry.group
        artist_text = "Artist(s): " + ", ".join(artists)
        # Append groups in brackets in case there are few artists, and they're not the same as the groups
        if groups and len(artists) <= 2 and groups != artists:
            artist_text += " (" + ", ".join(groups) + ")"
        painter.drawText(title_rect, Qt.AlignLeft, artist_text)

        # Prepare additional details
        details_list = []

        languages = [lang for lang in entry.language]
        # Remove translated from here since it's uninteresting
        if "translated" in languages:
            languages.remove("translated")

        if languages:
            details_list.append("Language: " + ", ".join(languages))

        details_list.append(f"Pages: {entry.pages}")

        # Check and append parody (if not just "original")
        parodies = entry.parody
        if parodies and 'original' not in parodies:
            details_list.append("Parody: " + ", ".join(parodies))

        details_text = " | ".join(details_list)

        # Move down to display additional details
        title_rect.translate(0, font_metrics.height())
        painter.drawText(title_rect, Qt.AlignLeft, details_text)

        # Display Id
        title_rect.translate(0, font_metrics.height())
        painter.drawText(title_rect, Qt.AlignLeft, "#" + entry.id)

        painter.setFont(original_font)

        self._render_tag_area(entry, title_rect, option, painter, original_font, background_color)

        painter.setFont(original_font)
        painter.setPen(self.base_pen_color)
        painter.restore()

    def _render_tag_area(self, entry, title_rect, option, painter, original_font, background_color):
        """
        Renders tags for an item within specified bounds. Adjusts text by wrapping or scaling to ensure it fits
        within its tag, while drawing each tag with a rounded background. Also renders upload text below them.
        """
        # Handle tags (showing only the first six tags)
        tags = entry.tags[:MAX_TAGS]

        # Start position for tags
        tag_x_start = title_rect.right() + TAG_SPACING
        tag_y_start = option.rect.top() + 2  # small offset to not start at the very top of the item
        for row in range(math.ceil(len(tags) / TAG_COLUMNS)):
            for col in range(TAG_COLUMNS):
                idx = row * TAG_COLUMNS + col
                if idx >= len(tags):
                    break
                tag_x = tag_x_start + col * (TAG_WIDTH + TAG_SPACING)
                tag_y = tag_y_start + row * (TAG_HEIGHT + TAG_SPACING)
                tag_rect = QRect(tag_x, tag_y, TAG_WIDTH, TAG_HEIGHT)

                # Scale the tag text
                painter.setFont(original_font)
                font = painter.font()
                font_metrics = QFontMetrics(font)

                tag_text = tags[idx]

                # Check if tag name fits without wrapping
                if font_metrics.width(tag_text) > tag_rect.width():
                    # Try wrapping the text
                    wrapped_text = "\n".join(
                        wordwrap(tag_text, width=tag_rect.width() / font_metrics.averageCharWidth()))

                    if font_metrics.boundingRect(tag_rect, Qt.AlignCenter,
                                                 wrapped_text).height() <= tag_rect.height() - 10:
                        tag_text = wrapped_text
                    else:
                        while (font_metrics.width(tag_text) > tag_rect.width() or
                               font_metrics.boundingRect(tag_rect, Qt.AlignCenter,
                                                         tag_text).height() > tag_rect.height()):
                            if font.pointSize() <= TAG_MINIMUM_FONT_SIZE:
                                break
                            font.setPointSize(font.pointSize() - 1)
                            painter.setFont(font)
                            font_metrics = QFontMetrics(font)

                # Draw background and text for the tag
                tag_path = QPainterPath()
                tag_path.addRoundedRect(QRectF(tag_rect), 5, 5)
                painter.fillPath(tag_path, blend_colors(TAG_BACKGROUND_COLOR, background_color, 0.7))
                # painter.strokePath(tag_path, QPen(QColor("#000000"), 1))  # draw border
                painter.drawText(tag_rect, Qt.AlignCenter | Qt.TextWordWrap, tag_text)
        painter.setFont(original_font)

        max_tag_y = tag_y_start + (math.ceil(len(tags) / TAG_COLUMNS)) * (TAG_HEIGHT + TAG_SPACING)
        upload_text_y_start = max_tag_y + 10

        upload_text = "Uploaded on: " + entry.upload

        remaining_space = option.rect.bottom() - max_tag_y  # Add small buffer so it doesn't reduce prematurely

        font = painter.font()
        font_metrics = QFontMetrics(font)

        while font_metrics.height() > remaining_space and font.pointSize() > TAG_MINIMUM_FONT_SIZE:
            font.setPointSize(font.pointSize() - 1)
            painter.setFont(font)
            font_metrics = QFontMetrics(font)

        painter.drawText(tag_x_start, upload_text_y_start, upload_text)

    # Defines size of item in the list
    def sizeHint(self, option, index):
        view_width = self.parent().width()
        item_width = (view_width - 25) // 2  # Two items per row
        view_column = self.parent().height()
        item_column = view_width // 18  # Four items per column
        return QSize(item_width, item_column)


class ImagePreview(QWidget):
    def __init__(self, mw, parent=None):
        super().__init__(parent)
        self.mw = mw
        self.setWindowFlags(Qt.ToolTip)  # Makes it float above other widgets
        self.setLayout(QVBoxLayout())
        self.label = QLabel(self)
        self.layout().addWidget(self.label)

        # Optional: Add shadow effect
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(10)
        effect.setColor(QColor(0, 0, 0, 80))
        effect.setOffset(1, 1)
        self.setGraphicsEffect(effect)

        self._last_image_id = None

    def set_image(self, id, max_width=250, max_height=300):
        if self._last_image_id != id:
            self._last_image_id = id
            thmb = self.mw.thumbnail_manager
            self.label.setPixmap(thmb.get_thumbnail(id).scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.adjustSize()


class SpecialListView(CustomListView):
    def __init__(self, parent=None):
        super(CustomListView, self).__init__(parent)
        self.mw = parent
        self.image_preview = ImagePreview(self.mw, self)
        self.setMouseTracking(True)
        # Amount of items to scroll
        self.scroll_speed = 1

    def mouseMoveEvent(self, event):
        self.show_image_preview(event)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.XButton1:  # Mouse button 4
            self.mw.manga_list_handler.navigate_back()
        elif event.button() == Qt.XButton2:  # Mouse button 5
            self.mw.manga_list_handler.navigate_forward()
        else:
            super(SpecialListView, self).mousePressEvent(event)

        # Hide the image preview if it's being shown
        self.image_preview.hide()

    def wheelEvent(self, event):
        # Get the number of degrees the wheel has rotated
        degrees = event.angleDelta() / 8
        # Get the number of steps the wheel has rotated (a step is 15 degrees)
        steps = degrees.y() // 15
        # Calculate the scroll distance
        scroll_distance = steps * self.scroll_speed
        # Scroll the view
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - scroll_distance)
        # Accept the event to indicate that it has been handled
        event.accept()
        self.show_image_preview(event)

    def leaveEvent(self, event):
        self.image_preview.hide()
        super().leaveEvent(event)

    # Stops scrolling to items that are still somewhat within view
    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        # Check if the item is visible
        if not self.isIndexVisible(index):
            super(SpecialListView, self).scrollTo(index, hint)

    def isIndexVisible(self, index):
        rect = self.visualRect(index)
        viewport_rect = self.viewport().rect()
        return viewport_rect.contains(QPoint(rect.left(), rect.top()))

    def show_image_preview(self, event):
        if self.mw.settings[thumbnail_preview]:
            # Fix bug that unshackles preview from leaveEvent when opening new window without leaving the app
            if not self.is_cursor_within_view(event.pos()):
                self.image_preview.hide()
                return

            index = self.indexAt(event.pos())
            if index.isValid():
                entry = index.data(Qt.UserRole)

                # Check if hovered item is the currently opened detail
                current_detail = self.mw.details_handler.cur_data
                if current_detail and current_detail.id == entry.id:
                    self.image_preview.hide()
                    return

                self.image_preview.set_image(entry.id)
                self.image_preview.move(event.globalPos() + QPoint(5, 5))
                self.image_preview.show()
            else:
                self.image_preview.hide()

    def is_cursor_within_view(self, cursor_pos):
        return self.viewport().rect().contains(cursor_pos)


class ThumbnailDelegate(QStyledItemDelegate):
    WIDTH, HEIGHT = 200, 200
    BATCH_SIZE = 6
    UPDATE_TIME_TREHSOLD = 250

    def __init__(self, mw, parent=None, *args, **kwargs):
        super(ThumbnailDelegate, self).__init__(parent, *args, **kwargs)
        self.mw = mw
        self.cache = {}
        self.img_star = (QPixmap(os.path.join(self.mw.image_path, 'star.png'))
                         .scaled(8, 8, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.img_good_story = (QPixmap(os.path.join(self.mw.image_path, 'good_story.png'))
                               .scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.img_good_art = (QPixmap(os.path.join(self.mw.image_path, 'good_art.png'))
                             .scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.threadPool = QThreadPool()
        self.imageLoader = ImageLoader(mw.thumbnail_manager)
        self.imageLoader.imageLoaded.connect(self.onImageLoaded)

        self.imagesSinceLastRefresh = set()
        self.batchSize = self.BATCH_SIZE  # Update viewport after these many images have loaded
        self.updateTimer = QTimer(self)
        self.updateTimer.setSingleShot(True)
        self.updateTimer.timeout.connect(self.processBatchUpdate)
        self.updateThreshold = self.UPDATE_TIME_TREHSOLD  # Time when to force an update if batch isn't met

    @pyqtSlot(str, QPixmap)
    def onImageLoaded(self, image_id, pixmap):
        self.cache[image_id] = pixmap
        self.imagesSinceLastRefresh.add(image_id)

        if len(self.imagesSinceLastRefresh) >= self.batchSize:
            self.processBatchUpdate()
        elif not self.updateTimer.isActive():
            self.updateTimer.start(self.updateThreshold)

    def paint(self, painter, option, index):
        # Retrieve item data from the model
        entry = index.data(Qt.UserRole)

        # Async Thumbnail loading
        thumbnail = None
        if self.mw.thumbnail_manager.id_to_pixmap.get(entry.id):
            thumbnail = self.mw.thumbnail_manager.get_thumbnail(entry.id)
        else:
            #thumbnail = self.mw.thumbnail_manager.default_img
            self.loadImageAsync(entry.id)

        title = entry.display_title()

        # Draw the background and border
        painter.save()

        # Reduce background opacity if removed
        if entry.removed:
            painter.setOpacity(0.2)

        background_color = DEFAULT_ITEM_BG_COLOR
        outline_thickness = 1
        outline_color = DEFAULT_ITEM_OUTLINE_COLOR

        if self.mw.details_handler.cur_data and self.mw.details_handler.cur_data.id == entry.id:
            background_color = option.palette.highlight().color()
            outline_thickness = 4
            outline_color = HIGHLIGHT_ITEM_OUTLINE_COLOR
        else:
            # Set collection-specific color
            collection_name = entry.collection
            if collection_name and collection_name in self.mw.collection_handler.collections:
                color = self.mw.collection_handler.collections[collection_name].get("color")
                if color:
                    background_color = blend_colors(DEFAULT_ITEM_BG_COLOR, QColor(color), 0.2)

            if option.state & QStyle.State_MouseOver:
                mod_color = QColor(255, 255, 255, 50)  # semi-transparent white to brighten the color
                background_color = blend_colors(background_color, mod_color, 0.8)

        item_path = QPainterPath()
        item_path.addRoundedRect(QRectF(option.rect), 5, 5)
        painter.fillPath(item_path, background_color)
        painter.restore()

        painter.save()
        if entry.removed:
            painter.setOpacity(0.2)

        if thumbnail:
            # Scale the thumbnail, maintaining aspect ratio
            max_thumb_height = option.rect.height()  # Use full height for the thumbnail
            scaled_thumb = thumbnail.scaled(self.WIDTH, max_thumb_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

            # Center the thumbnail horizontally and vertically in the item area
            thumb_x = option.rect.left() + (option.rect.width() - scaled_thumb.width()) / 2
            thumb_y = option.rect.top() + (option.rect.height() - scaled_thumb.height()) / 2  # Center vertically
            thumb_rect = QRect(int(thumb_x), int(thumb_y), int(scaled_thumb.width()), int(scaled_thumb.height()))
            painter.drawPixmap(thumb_rect, scaled_thumb)

        # Draw item outline later so it draws over the thumbnail
        painter.strokePath(item_path, QPen(outline_color, outline_thickness))

        painter.restore()
        painter.save()

        # Determine if the title needs to be split into two lines
        font_metrics = QFontMetrics(painter.font())
        title_line_1 = font_metrics.elidedText(title, Qt.ElideRight, option.rect.width())
        title_line_2 = None

        if title_line_1 != title:
            words = title.split()
            for i in range(len(words), 0, -1):
                possible_line_1 = " ".join(words[:i])
                if font_metrics.width(possible_line_1) <= option.rect.width() - 2:
                    title_line_1 = possible_line_1
                    title_line_2 = " ".join(words[i:])
                    break

        # Adjust the height of the title background based on whether the title is split
        line_height = 20
        title_background_height = line_height if title_line_2 is None else int(line_height * 2)

        # Draw semi-transparent background for the title on the bottom of the thumbnail
        title_background_rect = QRect(option.rect.left(), option.rect.bottom() - title_background_height + 1,
                                      option.rect.width(), title_background_height)
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.setPen(Qt.NoPen)  # No border
        corner_radius = 5
        painter.drawRoundedRect(title_background_rect, corner_radius, corner_radius)

        painter.restore()
        painter.save()

        # Draw the title, potentially split into two lines
        if title_line_2:
            line_height = title_background_height // 2
            first_line_rect = QRect(title_background_rect.left(), title_background_rect.top(),
                                    title_background_rect.width(), line_height)
            second_line_rect = QRect(title_background_rect.left(), title_background_rect.top() + line_height,
                                     title_background_rect.width(), line_height)

            title_line_2 = font_metrics.elidedText(title_line_2, Qt.ElideRight, second_line_rect.width())
            painter.drawText(first_line_rect, Qt.AlignCenter, title_line_1)
            painter.drawText(second_line_rect, Qt.AlignCenter, title_line_2)
        else:
            painter.drawText(title_background_rect, Qt.AlignCenter, title_line_1)

        # Define values for the below icons rendering
        icon_spacing = 5  # vertical height between icons
        rect_color = blend_colors(background_color, STAR_DIM_BG_COLOR, 0.7)
        rect_color.setAlpha(180)

        # Draw the score
        score = entry.score
        if score:
            star_width = self.img_star.width()
            star_height = self.img_star.height()
            total_height_for_stars = score * star_height + (score - 1) * icon_spacing

            # Calculating the top-left point to start drawing stars
            start_x = option.rect.x() + 5  # adding 8 pixels padding from left. Adjust as needed.
            start_y = option.rect.y() + 5  # center align vertically

            rect_width = star_width + 8
            rect_height = score * star_height + (score - 1) * icon_spacing + 10
            painter.setBrush(rect_color)
            painter.setPen(Qt.NoPen)
            # the 5,5 are the x,y radii of the rounded corners
            painter.drawRoundedRect(QRect(start_x - 4, start_y - 3, rect_width, rect_height), 5, 5)
            painter.restore()
            painter.save()

            for i in range(score):
                painter.drawPixmap(start_x, int(start_y + i * (star_height + icon_spacing)), self.img_star)

        # Calculate the required height for the backdrop rectangle
        backdrop_height = 0
        if entry.good_story():
            backdrop_height += self.img_good_story.height()
        if entry.good_art():
            backdrop_height += self.img_good_art.height()
        if entry.good_story() and entry.good_art():
            backdrop_height += icon_spacing  # Add space between icons

        if backdrop_height > 0:
            backdrop_rect = QRect(option.rect.right() - self.img_good_story.width() - 1,
                                  option.rect.top() + 3,
                                  self.img_good_story.width(),
                                  backdrop_height + 4)
            painter.setBrush(rect_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(backdrop_rect, 5, 5)

            # Draw the good story icon if applicable
            if entry.good_story():
                story_icon_pos = QPoint(backdrop_rect.left(), backdrop_rect.top() + 2)
                painter.drawPixmap(story_icon_pos, self.img_good_story)

            # Draw the good art icon if applicable
            if entry.good_art():
                art_icon_pos = QPoint(backdrop_rect.left(), backdrop_rect.top() + 2)
                if entry.good_story():
                    art_icon_pos.setY(art_icon_pos.y() + self.img_good_story.height() + icon_spacing)
                painter.drawPixmap(art_icon_pos, self.img_good_art)
        painter.restore()

    def loadImageAsync(self, image_id):
        worker = functools.partial(self.imageLoader.load, image_id)
        self.threadPool.start(worker)

    def processBatchUpdate(self):
        self.updateTimer.stop()
        self.parent().viewport().update()
        self.imagesSinceLastRefresh.clear()

    def sizeHint(self, option, index):
        return QSize(self.WIDTH, self.HEIGHT)  # Determins the size of the list entries


class ImageLoader(QObject):
    imageLoaded = pyqtSignal(str, QPixmap)

    def __init__(self, thumbnail_manager, parent=None):
        super().__init__(parent)
        self.thumbnail_manager = thumbnail_manager

    def load(self, image_id):
        image = self.thumbnail_manager.get_thumbnail(image_id)
        if image:
            self.imageLoaded.emit(image_id, image)
