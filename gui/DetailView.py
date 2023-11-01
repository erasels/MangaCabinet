import logging
import os

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPixmap, QPainter
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsScene, QGraphicsView, QHBoxLayout, QPushButton, \
    QApplication

from auxillary import Thumbnails


class DetailViewHandler(QWidget):
    DEFAULT_IMG = os.path.join("assets", "images", "no_thumbnail.png")

    def __init__(self, mw, entry):
        super(DetailViewHandler, self).__init__()
        self.mw = mw
        self.thumb = mw.thumbnail_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.entry = None
        self.init_ui(entry)

    def init_ui(self, entry):
        self.setGeometry(0, 0, 520, 520)
        self.setFixedSize(520, 520)
        self.setWindowTitle("Detail View")

        layout = QVBoxLayout()

        # Image
        self.image_scene = QGraphicsScene()
        self.image_view = QGraphicsView(self.image_scene, self)
        self.image_view.setFixedSize(500, 400)
        self.image_view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.image_view.setAlignment(Qt.AlignCenter)
        self.image_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.image_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Two Labels next to each other
        self.id_label = QLabel()
        self.artist_label = QLabel()

        label_layout = QHBoxLayout()
        label_layout.addWidget(self.id_label)
        label_layout.addWidget(self.artist_label)

        self.title_label = QLabel()

        # Two Buttons next to each other
        self.blur_btn = QPushButton("Blur")
        self.blur_btn.setStyleSheet(self.mw.styles.get("textbutton"))
        self.blur_btn.clicked.connect(self.blur)
        self.download_btn = QPushButton("Download new")
        self.download_btn.setStyleSheet(self.mw.styles.get("textbutton"))
        self.download_btn.clicked.connect(lambda: self.redownload())

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.blur_btn)
        btn_layout.addWidget(self.download_btn)

        layout.addWidget(self.image_view)
        layout.addWidget(self.title_label)
        layout.addLayout(label_layout)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.update_data(entry)

    def update_data(self, entry):
        if entry == self.entry:
            if not self.isVisible():
                self.set_position()
                self.show()
            return
        self.entry = entry

        self.load_image()

        self.id_label.setText(f"Id: {self.entry.id}")
        self.artist_label.setText(f"Artist: {', '.join(self.entry.artist)}")
        self.title_label.setText(f"Title: {self.entry.display_title()}")

        if not self.isVisible():
            self.set_position()
        self.show()

    def load_image(self):
        img_path = self.thumb.get_thumbnail_path(self.entry.id)
        if not img_path:
            img_path = DetailViewHandler.DEFAULT_IMG

        pixmap = QPixmap(img_path)
        scaled_pixmap = pixmap.scaled(self.image_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_scene.clear()
        self.image_scene.addPixmap(scaled_pixmap)

        self.image_scene.setSceneRect(QRectF(scaled_pixmap.rect()))

    def set_position(self):
        desired_position = self.mw.frameGeometry().topRight()

        # Check if this position would place the SecondWindow outside the screen
        screen_geometry = QApplication.desktop().screenGeometry(self.mw)
        if desired_position.x() + self.width() > screen_geometry.right():
            desired_position = self.mw.frameGeometry().topLeft()
            desired_position.setX(desired_position.x() - self.width())

        self.move(desired_position)

    def blur(self):
        img_path = self.thumb.get_thumbnail_path(self.entry.id)
        if img_path:
            Thumbnails.blur_image(img_path, img_path, 5)
            self.load_image()
        else:
            self.logger.warning("Tried to blur the default image.")

    def redownload(self, new_url=None):
        url = self.entry.thumbnail_url
        if new_url:
            url = new_url

        if url:
            self.thumb.download_thumbnail(url, self.thumb.make_file_path(self.entry), self.entry)
            self.load_image()
        else:
            self.logger.warning("Tried downloading thumbnail without thumbnail_url set.")