import logging

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QDialog, QVBoxLayout, QLabel, QLineEdit, QColorDialog, \
    QListWidget, QMenu, QWidget, QDialogButtonBox, QListWidgetItem

from auxillary.JSONMethods import load_json, save_json
from gui.WidgetDerivatives import RightClickableComboBox, DraggableListWidget


def fill_groups_box(groups, combobox):
    combobox.blockSignals(True)
    current_text = combobox.currentText()
    combobox.clear()
    combobox.addItem("None")
    for group in groups.keys():
        combobox.addItem(group, group)
    index = combobox.findText(current_text)
    # If the current text is not in the new list and was not "None", unblock signals before resetting to "None"
    if current_text not in groups and current_text != "None":
        combobox.blockSignals(False)
    # Set the index of the previously selected item, defaulting to "None" if not found
    combobox.setCurrentIndex(index if index != -1 else 0)
    # Emit the change to write it, removes the group from current selection however is inconsistent with other groups
    #combobox.currentIndexChanged.emit(combobox.currentIndex())
    if combobox.signalsBlocked():
        combobox.blockSignals(False)


class GroupHandler(QWidget):
    group_modified = pyqtSignal()

    def __init__(self, mw):
        super().__init__()
        self.group_list = None
        self.groups = load_json(mw.groups_file)
        self.mw = mw
        self.init_ui()

    def init_ui(self):
        self.group_combobox = RightClickableComboBox(self.mw)
        fill_groups_box(self.groups, self.group_combobox)
        self.group_combobox.setFixedWidth(100)
        self.group_combobox.setStyleSheet(self.mw.styles.get("dropdown"))
        self.group_combobox.currentIndexChanged.connect(lambda: self.mw.search_bar_handler.update_list())
        self.group_combobox.rightClicked.connect(lambda: self.group_combobox.setCurrentIndex(0))
        self.group_modified.connect(lambda: fill_groups_box(self.groups, self.group_combobox))

        self.manage_groups_btn = QPushButton("Manage Groups", self.mw)
        self.manage_groups_btn.clicked.connect(self.show_group_management_dialog)
        self.manage_groups_btn.setStyleSheet(self.mw.styles.get("textbutton"))

    def get_layout(self):
        groups_box = QHBoxLayout()
        groups_box.addWidget(self.group_combobox, 1)
        groups_box.addWidget(self.manage_groups_btn)
        return groups_box

    def get_widgets(self):
        return [self.group_combobox, self.manage_groups_btn]

    def show_group_management_dialog(self):
        dialog = GroupManagementDialog(self, self.mw, self.groups)
        dialog.exec_()


class GroupManagementDialog(QDialog):
    def __init__(self, parent, mw, groups):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mw = mw
        self.groups = groups
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Group Management')
        layout = QVBoxLayout(self)

        # Create the list view for groups
        self.group_list = DraggableListWidget(self)
        self.refresh_groups_list()
        self.group_list.setDragDropMode(QListWidget.InternalMove)
        self.group_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.group_list.customContextMenuRequested.connect(self.show_context_menu)
        self.group_list.itemMoved.connect(self.update_groups_order)
        self.parent().group_modified.connect(self.refresh_groups_list)
        layout.addWidget(self.group_list)

        self.setLayout(layout)

    def refresh_groups_list(self):
        self.group_list.clear()
        for group in self.groups.items():
            item = QListWidgetItem(group[0])
            col = group[1].get('color')
            if col:
                item.setBackground(QColor(col))
            desc = group[1].get('description')
            if desc:
                item.setToolTip(desc)
            self.group_list.addItem(item)

    def update_groups_order(self, from_index, to_index):
        if from_index == to_index:
            return

        # Extract the items as (key, value) pairs and move them
        items = list(self.groups.items())
        item = items.pop(from_index)
        items.insert(to_index, item)

        self.groups.clear()
        self.groups.update(items)
        save_json(self.mw.groups_file, self.groups)
        self.logger.debug("Reordered groups")
        self.parent().group_modified.emit()

    def show_context_menu(self, position):
        # Check if the right-click was on an item or empty space
        item = self.group_list.itemAt(position)
        if item is None:
            self.group_list.clearSelection()

        menu = QMenu()

        add_action = menu.addAction("Add Group")
        add_action.triggered.connect(self.add_group)

        edit_action = menu.addAction("Edit Group")
        edit_action.triggered.connect(self.edit_group)

        remove_action = menu.addAction("Remove Group")
        remove_action.triggered.connect(self.remove_group)

        # Disable edit and remove actions if no item is selected
        selected = self.group_list.selectedItems()
        edit_action.setVisible(bool(selected))
        remove_action.setVisible(bool(selected))

        menu.exec_(self.group_list.viewport().mapToGlobal(position))

    def add_group(self):
        self.manage_group()

    def remove_group(self):
        selected_items = self.group_list.selectedItems()
        if selected_items:
            group_name = selected_items[0].text()
            del self.groups[group_name]
            save_json(self.mw.groups_file, self.groups)
            self.logger.debug("Removed Group")
            self.parent().group_modified.emit()

    def edit_group(self):
        selected_items = self.group_list.selectedItems()
        if selected_items:
            group_name = selected_items[0].text()
            self.manage_group(group_name)

    def manage_group(self, group_name=None):
        dialog = QDialog(self.mw)
        layout = QVBoxLayout()

        # Name input
        name_label = QLabel("Group Name:", dialog)
        name_input = QLineEdit(dialog)
        name_input.setText(group_name if group_name else "")
        name_input.setReadOnly(bool(group_name))  # Group name is not editable if editing
        name_input.setStyleSheet(self.mw.styles.get("lineedit"))
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        # Description input
        desc_label = QLabel("Description:", dialog)
        desc_input = QLineEdit(dialog)
        desc_input.setText(self.groups.get(group_name, {}).get('description', '') if group_name else "")
        desc_input.setStyleSheet(self.mw.styles.get("lineedit"))
        layout.addWidget(desc_label)
        layout.addWidget(desc_input)

        # Color picker setup
        initial_color = QColor(self.groups[group_name].get('color')) if group_name else QColor()
        picked_color = [initial_color]
        pick_color_button = QPushButton("Pick Color", dialog)
        pick_color_button.setStyleSheet(f"background-color: {picked_color[0].name()};")
        layout.addWidget(pick_color_button)

        def update_button_color(color):
            if color.isValid():
                pick_color_button.setStyleSheet(f"background-color: {color.name()};")
                picked_color[0] = color

        def open_color_dialog():
            color_dialog = QColorDialog(initial_color, self.mw)
            color_dialog.setStyleSheet("\n".join(
                [self.mw.styles.get("textbutton"),
                 self.mw.styles.get("lineedit"),
                 self.mw.styles.get("spinbox")])
            )
            color_dialog.setPalette(self.mw.palette())

            if color_dialog.exec_():
                update_button_color(color_dialog.selectedColor())

        pick_color_button.clicked.connect(open_color_dialog)

        # Save and Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, dialog)
        button_box.setStyleSheet(self.mw.styles.get("textbutton"))
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        result = dialog.exec_()
        if result == QDialog.Accepted:
            group_name = group_name or name_input.text()
            group_desc = desc_input.text()
            isNew = group_name not in self.groups
            if isNew:
                self.groups[group_name] = {}

            if group_desc:
                self.groups[group_name]['description'] = group_desc

            if picked_color[0].isValid():
                self.groups[group_name]['color'] = picked_color[0].name()

            save_json(self.mw.groups_file, self.groups)
            self.logger.debug(f"{'Added' if isNew else 'Modified'} Group {group_name} with values: {self.groups[group_name]}")
            self.parent().group_modified.emit()
