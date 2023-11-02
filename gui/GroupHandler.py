from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QDialog, QVBoxLayout, QLabel, QLineEdit, QColorDialog

from auxillary.JSONMethods import load_json, save_json
from gui.WidgetDerivatives import RightClickableComboBox


class GroupHandler(QObject):
    group_added = pyqtSignal(str)

    def __init__(self, mw):
        super().__init__()
        self.add_group_btn = None
        self.group_combobox = None
        self.groups = load_json(mw.groups_file)
        self.mw = mw
        self.init_ui()

    def init_ui(self):
        self.group_combobox = RightClickableComboBox(self.mw)
        self.group_combobox.addItem("None", None)
        for group_name, group_details in self.groups.items():
            self.group_combobox.addItem(group_name, group_name)
        self.group_combobox.setFixedWidth(100)

        self.group_combobox.currentIndexChanged.connect(lambda: self.mw.search_bar_handler.update_list())
        self.group_combobox.rightClicked.connect(lambda: self.group_combobox.setCurrentIndex(0))
        self.group_added.connect(lambda grp: self.group_combobox.addItem(grp))
        self.group_combobox.setStyleSheet(self.mw.styles.get("dropdown"))

        self.add_group_btn = QPushButton("New Group", self.mw)
        self.add_group_btn.clicked.connect(self.add_group)
        self.add_group_btn.setStyleSheet(self.mw.styles.get("textbutton"))

    # In case I want to make this its own bar
    def get_layout(self):
        groups_box = QHBoxLayout()
        groups_box.addWidget(self.group_combobox, 1)
        groups_box.addWidget(self.add_group_btn)
        return groups_box

    def get_widgets(self):
        return [self.group_combobox, self.add_group_btn]

    # Method to add new group creation window
    def add_group(self):
        dialog = QDialog(self.mw)
        layout = QVBoxLayout()

        # Name input
        name_label = QLabel("Group Name:", dialog)
        name_input = QLineEdit(dialog)
        name_input.setStyleSheet(self.mw.styles.get("lineedit"))

        layout.addWidget(name_label)
        layout.addWidget(name_input)

        # Color picker setup
        picked_color = [QColor()]
        pick_color_button = QPushButton("Pick Color", dialog)
        pick_color_button.setStyleSheet(self.mw.styles.get("textbutton"))
        layout.addWidget(pick_color_button)

        # Update the button's background color to show the picked color
        def update_button_color(color):
            pick_color_button.setStyleSheet(f"background-color: {color.name()};")
            picked_color[0] = color

        pick_color_button.clicked.connect(lambda: update_button_color(QColorDialog.getColor()))

        # Save and Cancel buttons
        save_btn = QPushButton("Save", dialog)
        save_btn.clicked.connect(dialog.accept)
        save_btn.setStyleSheet(self.mw.styles.get("textbutton"))
        cancel_btn = QPushButton("Cancel", dialog)
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet(self.mw.styles.get("textbutton"))
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        dialog.setLayout(layout)

        result = dialog.exec_()
        if result == QDialog.Accepted:
            group_name = name_input.text()
            isNew = False
            if group_name not in self.groups:
                self.groups[group_name] = {}
                isNew = True
            if picked_color[0].isValid():
                self.groups[group_name].update({"color": picked_color[0].name()})
            save_json(self.mw.groups_file, self.groups)
            if isNew:
                # Add to the combobox
                self.group_added.emit(group_name)
    
    