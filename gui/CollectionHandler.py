import logging

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QDialog, QVBoxLayout, QLabel, QLineEdit, QColorDialog, \
    QListWidget, QMenu, QWidget, QDialogButtonBox, QListWidgetItem

from auxillary.JSONMethods import load_json, save_json
from gui.WidgetDerivatives import RightClickableComboBox, DraggableListWidget


def fill_collections_box(collections, combobox):
    combobox.blockSignals(True)
    current_text = combobox.currentText()
    combobox.clear()
    combobox.addItem("None")
    for collection in collections.keys():
        combobox.addItem(collection, collection)
    index = combobox.findText(current_text)
    # If the current text is not in the new list and was not "None", unblock signals before resetting to "None"
    if current_text not in collections and current_text != "None":
        combobox.blockSignals(False)
    # Set the index of the previously selected item, defaulting to "None" if not found
    combobox.setCurrentIndex(index if index != -1 else 0)
    # Emit the change to write it, removes the collection from current selection however is inconsistent with other collections
    #combobox.currentIndexChanged.emit(combobox.currentIndex())
    if combobox.signalsBlocked():
        combobox.blockSignals(False)


class CollectionHandler(QWidget):
    collection_modified = pyqtSignal()

    def __init__(self, mw):
        super().__init__()
        self.collection_to_index = None
        self.collection_list = None
        self.collections = load_json(mw.collections_file)
        self.update_index_mapping()
        self.mw = mw
        self.init_ui()

    def init_ui(self):
        self.collection_combobox = RightClickableComboBox(self.mw)
        fill_collections_box(self.collections, self.collection_combobox)
        self.collection_combobox.setFixedWidth(150)
        self.collection_combobox.setStyleSheet(self.mw.styles.get("dropdown"))
        self.collection_combobox.currentIndexChanged.connect(lambda: self.mw.search_bar_handler.update_list())
        self.collection_combobox.rightClicked.connect(lambda: self.collection_combobox.setCurrentIndex(0))
        self.collection_modified.connect(lambda: fill_collections_box(self.collections, self.collection_combobox))
        self.collection_modified.connect(lambda: self.update_index_mapping())

        self.manage_collections_btn = QPushButton("Manage Collections", self.mw)
        self.manage_collections_btn.clicked.connect(self.show_collection_management_dialog)
        self.manage_collections_btn.setStyleSheet(self.mw.styles.get("textbutton"))

    def get_layout(self):
        collections_box = QHBoxLayout()
        collections_box.addWidget(self.collection_combobox, 1)
        collections_box.addWidget(self.manage_collections_btn)
        return collections_box

    def get_widgets(self):
        return [self.collection_combobox, self.manage_collections_btn]

    def show_collection_management_dialog(self):
        dialog = CollectionManagementDialog(self, self.mw, self.collections)
        dialog.exec_()

    def update_index_mapping(self):
        self.collection_to_index = {key: index for index, key in enumerate(self.collections.keys())}


class CollectionManagementDialog(QDialog):
    def __init__(self, parent, mw, collections):
        super().__init__(parent)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mw = mw
        self.collections = collections
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Collection Management')
        layout = QVBoxLayout(self)

        # Create the list view for collections
        self.collection_list = DraggableListWidget(self)
        self.refresh_collections_list()
        self.collection_list.setDragDropMode(QListWidget.InternalMove)
        self.collection_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.collection_list.customContextMenuRequested.connect(self.show_context_menu)
        self.collection_list.itemMoved.connect(self.update_collections_order)
        self.parent().collection_modified.connect(self.refresh_collections_list)
        layout.addWidget(self.collection_list)

        self.setLayout(layout)

    def refresh_collections_list(self):
        self.collection_list.clear()
        for collection in self.collections.items():
            item = QListWidgetItem(collection[0])
            col = collection[1].get('color')
            if col:
                item.setBackground(QColor(col))
            desc = collection[1].get('description')
            if desc:
                item.setToolTip(desc)
            self.collection_list.addItem(item)

    def update_collections_order(self, from_index, to_index):
        if from_index == to_index:
            return

        # Extract the items as (key, value) pairs and move them
        items = list(self.collections.items())
        item = items.pop(from_index)
        items.insert(to_index, item)

        self.collections.clear()
        self.collections.update(items)
        save_json(self.mw.collections_file, self.collections)
        self.logger.debug("Reordered collections")
        self.parent().collection_modified.emit()

    def show_context_menu(self, position):
        # Check if the right-click was on an item or empty space
        item = self.collection_list.itemAt(position)
        if item is None:
            self.collection_list.clearSelection()

        menu = QMenu()

        add_action = menu.addAction("Add Collection")
        add_action.triggered.connect(self.add_collection)

        edit_action = menu.addAction("Edit Collection")
        edit_action.triggered.connect(self.edit_collection)

        remove_action = menu.addAction("Remove Collection")
        remove_action.triggered.connect(self.remove_collection)

        # Disable edit and remove actions if no item is selected
        selected = self.collection_list.selectedItems()
        edit_action.setVisible(bool(selected))
        remove_action.setVisible(bool(selected))

        menu.exec_(self.collection_list.viewport().mapToGlobal(position))

    def add_collection(self):
        self.manage_collection()

    def remove_collection(self):
        selected_items = self.collection_list.selectedItems()
        if selected_items:
            collection_name = selected_items[0].text()
            del self.collections[collection_name]
            save_json(self.mw.collections_file, self.collections)
            self.logger.debug("Removed Collection")
            self.parent().collection_modified.emit()

    def edit_collection(self):
        selected_items = self.collection_list.selectedItems()
        if selected_items:
            collection_name = selected_items[0].text()
            self.manage_collection(collection_name)

    def manage_collection(self, collection_name=None):
        dialog = QDialog(self.mw)
        layout = QVBoxLayout()

        # Name input
        name_label = QLabel("Collection Name:", dialog)
        name_input = QLineEdit(dialog)
        name_input.setText(collection_name if collection_name else "")
        name_input.setReadOnly(bool(collection_name))  # Collection name is not editable if editing
        name_input.setStyleSheet(self.mw.styles.get("lineedit"))
        layout.addWidget(name_label)
        layout.addWidget(name_input)

        # Description input
        desc_label = QLabel("Description:", dialog)
        desc_input = QLineEdit(dialog)
        desc_input.setText(self.collections.get(collection_name, {}).get('description', '') if collection_name else "")
        desc_input.setStyleSheet(self.mw.styles.get("lineedit"))
        layout.addWidget(desc_label)
        layout.addWidget(desc_input)

        # Color picker setup
        initial_color = QColor(self.collections[collection_name].get('color')) if collection_name else QColor()
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
            collection_name = collection_name or name_input.text()
            collection_desc = desc_input.text()
            isNew = collection_name not in self.collections
            if isNew:
                self.collections[collection_name] = {}

            if collection_desc:
                self.collections[collection_name]['description'] = collection_desc

            if picked_color[0].isValid():
                self.collections[collection_name]['color'] = picked_color[0].name()

            save_json(self.mw.collections_file, self.collections)
            self.logger.debug(f"{'Added' if isNew else 'Modified'} Collection {collection_name} with values: {self.collections[collection_name]}")
            self.parent().collection_modified.emit()
