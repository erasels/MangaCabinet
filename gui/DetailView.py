import logging

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, \
    QApplication, QCheckBox

from auxillary import Thumbnails
from gui.Options import show_removed
from gui.WidgetDerivatives import ImageViewer


class DetailViewHandler(QWidget):
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

        self.image_viewer = ImageViewer(self.mw.thumbnail_manager, parent=self)
        self.image_viewer.setFixedSize(500, 400)

        self.id_label = QLabel()
        self.artist_label = QLabel()
        self.pages_label = QLabel()
        self.remove_checkbox = QCheckBox("Marked removed", self)
        self.remove_checkbox.stateChanged.connect(self.update_removed_status)

        details_layout = QHBoxLayout()
        details_layout.addWidget(self.id_label)
        details_layout.addWidget(self.artist_label)
        details_layout.addWidget(self.pages_label)
        details_layout.addWidget(self.remove_checkbox)

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

        layout.addWidget(self.image_viewer)
        layout.addWidget(self.title_label)
        layout.addLayout(details_layout)
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

        self.image_viewer.load_image(self.entry.id)

        self.id_label.setText(f"Id: {self.entry.id}")
        self.artist_label.setText(f"Artist: {', '.join(self.entry.artist)}")
        self.title_label.setText(f"Title: {self.entry.display_title()}")
        self.pages_label.setText(f"Pages: {self.entry.pages}")
        self.remove_checkbox.setChecked(self.entry.removed)

        if not self.isVisible():
            self.set_position()
        self.show()

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
            self.thumb.update_thumbnail(self.entry.id, img_path)
            self.image_viewer.load_image(self.entry.id)
        else:
            self.logger.warning("Tried to blur the default image.")

    def redownload(self, new_url=None):
        url = self.entry.thumbnail_url
        if new_url:
            url = new_url

        if url:
            self.thumb.download_thumbnail(url, self.thumb.make_file_path(self.entry), self.entry)
            self.image_viewer.load_image(self.entry.id)
        else:
            self.logger.warning("Tried downloading thumbnail without thumbnail_url set.")

    def update_removed_status(self, state):
        self.entry.removed = state == Qt.Checked
        self.mw.is_data_modified = True
        self.entry.update_last_edited()
        self.logger.debug(f"{self.entry.id}: removed was updated with: deleted {self.entry.removed}")

        if not self.mw.settings[show_removed]:
            self.mw.search_bar_handler.update_list()
