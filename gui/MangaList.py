from PyQt5.QtCore import Qt, QRect, QSize, QRectF
from PyQt5.QtGui import QColor, QPen, QFontMetrics, QPainterPath
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle


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


# Constants for tags
TAG_WIDTH = 60
TAG_HEIGHT = 20
TAG_SPACING = 3
TAG_COLUMNS = 3
TAG_MINIMUM_FONT_SIZE = 5
TAG_BACKGROUND_COLOR = QColor("#D6D6D6")


class MangaDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):
        # Retrieve item data from the model
        entry = index.data(Qt.UserRole)

        # Draw the background and border
        painter.save()
        background_color = QColor("#F9F9F9")  # default background color

        # Set group-specific color
        group_name = entry.group
        if group_name and group_name in self.parent().parent().groups:
            color = self.parent().parent().groups[group_name].get("color")
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

        # Draw the title and handle long titles
        title = entry.display_title()
        title_rect = option.rect.adjusted(10, 10, -10, -10)  # Adjust as necessary

        # Calculate total width for three tags with their spacing
        tags_total_width = TAG_COLUMNS * TAG_WIDTH + (TAG_COLUMNS - 1) * TAG_SPACING

        # Adjust title rectangle width to avoid overlap with tags
        title_rect.setWidth(title_rect.width() - tags_total_width)

        # Use QFontMetrics to elide the text if it's too long
        font_metrics = QFontMetrics(painter.font())

        # Handle Title with a potential line break
        words = title.split()
        line1, line2 = "", ""
        while words and font_metrics.width(line1 + words[0]) < title_rect.width():
            line1 += (words.pop(0) + " ")
        while words and font_metrics.width(line2 + words[0]) < title_rect.width():
            line2 += (words.pop(0) + " ")

        if words:  # If there are still words left, add '...' to line2
            line2 = font_metrics.elidedText(line2, Qt.ElideRight, title_rect.width())

        painter.drawText(title_rect, Qt.AlignLeft, line1.strip())
        title_rect.translate(0, font_metrics.height())  # Move down for second line
        painter.drawText(title_rect, Qt.AlignLeft, line2.strip())

        # Handle tags (showing only the first six tags)
        tags = entry.tags[:6]  # TODO: Add logic to show important/interesting tags

        # Start position for tags
        tag_x_start = title_rect.right() + TAG_SPACING
        tag_y_start = option.rect.center().y() - (2 * TAG_HEIGHT + TAG_SPACING) // 2
        original_font = painter.font()
        for row in range(2):
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
                while font_metrics.width(tags[idx]) > tag_rect.width() and font.pointSize() > TAG_MINIMUM_FONT_SIZE:  # Minimum font size of 5
                    font.setPointSize(font.pointSize() - 1)
                    painter.setFont(font)
                    font_metrics = QFontMetrics(font)

                # Draw background and text for the tag
                tag_path = QPainterPath()
                tag_path.addRoundedRect(QRectF(tag_rect), 5, 5)
                painter.fillPath(tag_path, TAG_BACKGROUND_COLOR)
                painter.strokePath(tag_path, QPen(QColor("#000000"), 1))  # draw border
                painter.drawText(tag_rect, Qt.AlignCenter, tags[idx])
        painter.setFont(original_font)

    def sizeHint(self, option, index):
        return QSize(200, 60)
