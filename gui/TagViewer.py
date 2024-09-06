from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QComboBox, QListWidget, QHBoxLayout, QApplication


class TagViewer(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.tag_data = mw.tag_data
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Tag Viewer')
        self.setGeometry(0, 0, 600, 400)

        self.layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()

        # Search bar
        self.search_bar = QLineEdit(self)
        self.search_bar.setStyleSheet(self.mw.styles["lineedit"])
        self.search_bar.setPlaceholderText('Search tags...')
        self.search_bar.textChanged.connect(self.sort_and_display_tags)
        search_layout.addWidget(self.search_bar)

        # Sort options
        self.sort_combo = QComboBox(self)
        self.sort_combo.setStyleSheet(self.mw.styles["sorter"])
        self.sort_combo.addItems(['By Count', 'By Name'])
        self.sort_combo.currentIndexChanged.connect(self.sort_and_display_tags)
        search_layout.addWidget(self.sort_combo)

        self.layout.addLayout(search_layout)

        # List widget for tags
        self.list_widget = QListWidget(self)
        self.layout.addWidget(self.list_widget)

    def sort_and_display_tags(self):
        tags = self.filter_tags()
        sort_by = self.sort_combo.currentText()

        if sort_by == 'By Name':
            tags.sort(key=lambda x: x[0].lower())  # Sort by tag name (case-insensitive)
        elif sort_by == 'By Count':
            tags.sort(key=lambda x: x[1]['count'], reverse=True)  # Sort by tag count

        self.display_tags(tags)

    def display_tags(self, tags):
        self.list_widget.clear()
        for tag, data in tags:
            self.list_widget.addItem(f"{tag} ({data['count']})")

    def filter_tags(self):
        search_text = self.search_bar.text().lower()
        if search_text:
            tags = [(tag, data) for tag, data in self.tag_data.items() if search_text in tag.lower()]
        else:
            tags = [(tag, data) for tag, data in self.tag_data.items()]
        return tags

    def set_position(self):
        desired_position = self.mw.frameGeometry().topLeft()
        desired_position.setX(desired_position.x() - self.width())

        # Check if this position would place the SecondWindow outside the screen
        screen_geometry = QApplication.desktop().screenGeometry(self.mw)
        if desired_position.x() < screen_geometry.left():
            desired_position = self.mw.frameGeometry().topRight()
            desired_position.setX(desired_position.x())

        self.move(desired_position)

    def show(self):
        self.sort_and_display_tags()
        if not self.isVisible():
            self.set_position()
            super().show()
