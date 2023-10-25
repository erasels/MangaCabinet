import math
import typing

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QRect, QSize, QRectF
from PyQt5.QtGui import QColor, QPen, QFontMetrics, QPainterPath, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle, QListView


class ListViewHandler:
    def __init__(self, parent):
        self.list_delegate = None
        self.list_model = None
        self.list_view = None
        self.mw = parent
        self.init_ui()

    def init_ui(self):
        # List view
        self.list_view = QListView(self.mw)
        self.list_model = QStandardItemModel(self.list_view)
        self.list_view.setModel(self.list_model)

        self.list_view.setWrapping(True)
        self.list_view.setFlow(QListView.LeftToRight)
        self.list_view.setLayoutMode(QListView.Batched)

        self.list_delegate = MangaDelegate(self.mw, self.list_view)
        self.list_view.setItemDelegate(self.list_delegate)
        self.list_view.clicked.connect(self.mw.details_handler.display_detail)

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
TAG_BACKGROUND_COLOR = QColor("#D6D6D6")

TITLE_MINIMUM_FONT_SIZE = 7


class MangaDelegate(QStyledItemDelegate):

    def __init__(self, main_window, parent: typing.Optional[QtCore.QObject] = ...):
        super().__init__(parent)
        self.mw = main_window

    def paint(self, painter, option, index):
        # Retrieve item data from the model
        entry = index.data(Qt.UserRole)

        # Draw the background and border
        painter.save()
        background_color = QColor("#F0F0F0")  # default background color

        # Set group-specific color
        group_name = entry.group
        if group_name and group_name in self.mw.group_handler.groups:
            color = self.mw.group_handler.groups[group_name].get("color")
            if color:
                background_color = QColor(color)

        if option.state & QStyle.State_MouseOver:
            dim_color = QColor(0, 0, 0, 50)  # semi-transparent black to dim the color
            background_color = blend_colors(background_color, dim_color, 0.7)

        if option.state & QStyle.State_Selected:
            background_color = option.palette.highlight().color()

        item_path = QPainterPath()
        item_path.addRoundedRect(QRectF(option.rect), 5, 5)
        painter.fillPath(item_path, background_color)
        painter.strokePath(item_path, QPen(QColor("#B6B6B6"), 1))
        painter.restore()

        # Draw the title
        title = entry.display_title()
        title_rect = option.rect.adjusted(10, 10, -10, -10)  # Adjust as necessary
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

        painter.drawText(title_rect, Qt.AlignLeft, title)

        # Move down for authors
        title_rect.translate(0, font_metrics.height())
        painter.setFont(original_font)

        # Display the authors
        authors = entry.author
        author_text = "Artist(s): " + ", ".join(authors)
        painter.drawText(title_rect, Qt.AlignLeft, author_text)

        # Prepare additional details
        details_list = []

        # Check and append language
        languages = entry.language
        if languages:
            details_list.append("Language: " + ", ".join(languages))

        # Append page count
        details_list.append(f"Pages: {entry.pages}")

        # Check and append parody (if not just "original")
        parodies = entry.parody
        if parodies and 'original' not in parodies:
            details_list.append("Parody: " + ", ".join(parodies))

        # Concatenate the details
        details_text = " | ".join(details_list)

        # Move down to display additional details
        title_rect.translate(0, font_metrics.height())
        painter.drawText(title_rect, Qt.AlignLeft, details_text)

        painter.setFont(original_font)

        self._render_tag_area(entry, title_rect, option, painter, original_font, background_color)

        painter.setFont(original_font)

    def _render_tag_area(self, entry, title_rect, option, painter, original_font, background_color):
        """
        Renders tags for an item within specified bounds. Adjusts text by wrapping or scaling to ensure it fits
        within its tag, while drawing each tag with a rounded background. Also renders upload text below them.
        """
        # Handle tags (showing only the first six tags)
        tags = entry.tags[:MAX_TAGS]  # TODO: Add logic to show important/interesting tags

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
                if font_metrics.boundingRect(tag_rect, Qt.AlignCenter,
                                             tag_text).height() > tag_rect.height() or font_metrics.width(tag_text) > tag_rect.width():
                    # Try wrapping the text
                    wrapped_text = "\n".join(
                        wordwrap(tag_text, width=tag_rect.width() / font_metrics.averageCharWidth()))

                    if font_metrics.boundingRect(tag_rect, Qt.AlignCenter, wrapped_text).height() <= tag_rect.height():
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
                painter.fillPath(tag_path, blend_colors(TAG_BACKGROUND_COLOR, background_color, 0.85))
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
