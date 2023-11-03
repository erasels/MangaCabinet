import math
import os
import typing

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QRect, QSize, QRectF, QPoint
from PyQt5.QtGui import QColor, QPen, QFontMetrics, QPainterPath, QStandardItemModel, QStandardItem, QPixmap
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle, QListView, QAbstractItemView, QWidget, QVBoxLayout, \
    QLabel, QGraphicsDropShadowEffect

from gui.Options import thumbnail_preview
from gui.WidgetDerivatives import CustomListView


class ListViewHandler:
    def __init__(self, parent):
        self.list_delegate = None
        self.list_model = None
        self.list_view = None
        self.mw = parent
        self.init_ui()

    def init_ui(self):
        # List view
        self.list_view = SpecialListView(self.mw)
        self.list_model = QStandardItemModel(self.list_view)
        self.list_view.setModel(self.list_model)

        self.list_view.setWrapping(True)
        self.list_view.setFlow(QListView.LeftToRight)
        self.list_view.setLayoutMode(QListView.Batched)

        self.list_delegate = MangaDelegate(self.mw, self.list_view)
        self.list_view.setItemDelegate(self.list_delegate)
        # Prevent editing on double-click
        self.list_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.list_view.clicked.connect(self.mw.details_handler.display_detail)
        self.list_view.clicked.connect(lambda index: self.list_view.dataChanged(index, index))
        self.list_view.middleClicked.connect(self.open_tab)
        self.list_view.rightClicked.connect(lambda index: self.mw.open_detail_view(index.data(Qt.UserRole)))

    def get_widget(self):
        return self.list_view

    def handle_resize(self):
        self.list_view.updateGeometries()
        self.list_view.doItemsLayout()  # Force the view to relayout items.

    def clear_view(self):
        self.list_model.clear()

    def add_item(self, entry):
        item = QStandardItem()
        item.setData(entry, Qt.UserRole)
        self.list_model.appendRow(item)

    def open_tab(self, index):
        self.mw.browser_handler.open_tab(index.data(Qt.UserRole))


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

        if not self.base_pen_color:
            self.base_pen_color = painter.pen().color()

        background_color = DEFAULT_ITEM_BG_COLOR

        # Set group-specific color
        group_name = entry.group
        if group_name and group_name in self.mw.group_handler.groups:
            color = self.mw.group_handler.groups[group_name].get("color")
            if color:
                background_color = blend_colors(DEFAULT_ITEM_BG_COLOR, QColor(color), 0.2)

        if option.state & QStyle.State_MouseOver:
            mod_color = QColor(255, 255, 255, 50)  # semi-transparent white to brighten the color
            background_color = blend_colors(background_color, mod_color, 0.8)

        if self.mw.details_handler.cur_data and self.mw.details_handler.cur_data.id == entry.id:
            background_color = option.palette.highlight().color()

        item_path = QPainterPath()
        item_path.addRoundedRect(QRectF(option.rect), 5, 5)
        painter.fillPath(item_path, background_color)
        painter.strokePath(item_path, QPen(QColor("#666666"), 1))
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
        groups = entry.artist_group
        artist_text = "Artist(s): " + ", ".join(artists)
        # Append groups in brackets in case there are few artists, and they're not the same as the groups
        if groups and len(artists) <= 2 and groups != artists:
            artist_text += " (" + ", ".join(groups) + ")"
        painter.drawText(title_rect, Qt.AlignLeft, artist_text)

        # Prepare additional details
        details_list = []

        languages = entry.language
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

        painter.setFont(original_font)

        self._render_tag_area(entry, title_rect, option, painter, original_font, background_color)

        painter.setFont(original_font)
        painter.setPen(self.base_pen_color)

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
    def __init__(self, parent=None):
        super().__init__(parent)
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

        self._last_image_path = None
        self._cached_pixmap = None

    def set_image(self, image_path, max_width=250, max_height=300):
        if self._last_image_path != image_path:
            self._cached_pixmap = QPixmap(image_path).scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self._last_image_path = image_path
            self.label.setPixmap(self._cached_pixmap)
            self.adjustSize()


class SpecialListView(CustomListView):
    def __init__(self, parent=None):
        super(CustomListView, self).__init__(parent)
        self.mw = parent
        self.image_preview = ImagePreview(self)
        self.setMouseTracking(True)

    def mouseMoveEvent(self, event):
        self.show_image_preview(event)
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.image_preview.hide()

    def wheelEvent(self, event):
        self.show_image_preview(event)
        super().wheelEvent(event)

    def leaveEvent(self, event):
        self.image_preview.hide()
        super().leaveEvent(event)

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

                image_path = self.mw.thumbnail_manager.get_thumbnail_path(entry.id)
                if image_path:
                    self.image_preview.set_image(image_path)
                    self.image_preview.move(event.globalPos() + QPoint(5, 5))
                    self.image_preview.show()
                    return
            self.image_preview.hide()
            return

    def is_cursor_within_view(self, cursor_pos):
        return self.viewport().rect().contains(cursor_pos)
