import json

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem
from PyQt5.QtWidgets import QLineEdit, QLabel, QHBoxLayout

from gui.ComboBoxDerivatives import RightClickableComboBox
from gui.Options import search_thrshold, loose_match


class SearchBarHandler:

    def __init__(self, main_window):
        self.sort_combobox = None
        self.hits_label = None
        self.search_bar = None
        self.mw = main_window
        self.sort_order_reversed = False
        self.showing_all_entries = False
        self.sorting_options = [
            ("By id", lambda entry: entry.id),
            ("By upload date", lambda entry: (0 if entry.upload is None else 1, entry.upload_date())),
            ("By data order", lambda entry: self.mw.entry_to_index_reversed.get(entry.id, 0)),
            ("By name", lambda entry: [-ord(ch) for ch in entry.display_title().lower()]),
            ("By score", lambda entry: entry.get('score', float('-inf')))
        ]
        self.init_ui()

    def init_ui(self):
        # Search bar
        self.search_bar = QLineEdit(self.mw)
        self.search_bar.textChanged.connect(lambda: self.update_list(False))
        self.search_bar.setStyleSheet(self.mw.styles.get("lineedit"))
        self.search_bar.setPlaceholderText("Search...")

        # Hits label
        self.hits_label = QLabel(self.mw)
        self.hits_label.hide()

        # Sorting combo box
        self.sort_combobox = RightClickableComboBox()
        for name, _ in self.sorting_options:
            self.sort_combobox.addItem(name)
        self.sort_combobox.currentIndexChanged.connect(lambda: self.update_list())
        self.sort_combobox.rightClicked.connect(self.toggle_sort_order)
        self.sort_combobox.setStyleSheet(self.mw.styles.get("sorter"))
        self.sort_combobox.setObjectName("Normal")

    def get_layout(self, options_button):
        search_box = QHBoxLayout()  # Create a horizontal box layout
        search_box.addWidget(self.search_bar, 1)  # The '1' makes the search bar expand to fill available space
        search_box.addWidget(self.hits_label)
        search_box.addWidget(self.sort_combobox)
        search_box.addWidget(options_button)
        return search_box

    def toggle_sort_order(self):
        if self.sort_order_reversed:
            self.sort_combobox.setObjectName("Normal")
        else:
            self.sort_combobox.setObjectName("Reversed")
        self.sort_combobox.setStyleSheet(self.mw.styles["sorter"])  # Refresh the stylesheet to force the update.
        self.sort_order_reversed = not self.sort_order_reversed
        self.update_list()

    def secondary_sort_key(self, x):
        sort_func = self.sorting_options[self.sort_combobox.currentIndex()][1]
        return sort_func(x[0])

    def update_list(self, forceRefresh=True):
        search_terms = [term.strip() for term in self.search_bar.text().split(",")]

        # Define sort in case we need it
        _, sort_func = self.sorting_options[self.sort_combobox.currentIndex()]
        selected_group = self.mw.group_handler.group_combobox.currentData()

        if not selected_group:
            mod_data = self.mw.data
        else:
            # Can be optimized in case update_list gets called a lot
            mod_data = [manga_entry for manga_entry in self.mw.data if manga_entry.group == selected_group]

        # If less than 3 characters and already showing all entries, return early
        if len(self.search_bar.text()) < 3:
            if self.showing_all_entries and not forceRefresh:
                return
            else:
                sorted_data = sorted(mod_data, key=lambda x: sort_func(x), reverse=not self.sort_order_reversed)
                self.mw.manga_list_handler.clear_view()
                for entry in sorted_data:
                    self.mw.manga_list_handler.add_item(entry)
                self.showing_all_entries = True
                self.hits_label.hide()
                return

        # Compute scores for all manga entries and sort them based on the score
        scored_data = [(entry, self.match_score(entry, search_terms)) for entry in mod_data]
        sorted_data = sorted(scored_data, key=lambda x: (-x[1], self.secondary_sort_key(x) * (-1 if not self.sort_order_reversed else 1)))

        self.mw.manga_list_handler.clear_view()  # Clear the list before adding filtered results

        hit_count = 0
        threshold = self.mw.settings[search_thrshold]
        for idx, (entry, score) in enumerate(sorted_data):
            if score > 0:
                hit_count += 1
                if threshold == 0 or idx < threshold:  # Show all entries if Threshold is 0
                    self.mw.manga_list_handler.add_item(entry)
            else:
                break

        if hit_count > 0 and search_terms:
            self.hits_label.setText(f"Hits: {hit_count}")
            self.hits_label.show()
        else:
            self.hits_label.hide()

        self.showing_all_entries = False

    def match_score(self, data, terms):
        """Compute a score based on the number of matching terms."""
        score = 0

        for term in terms:
            term_score = 0
            if ":" in term:
                field, value = term.split(":", 1)
                data_value = data.get(field, "")
                if value and value[0] in [">", "<"]:
                    term_score = self.compare_match(data_value, value)
                else:
                    term_score = self.count_matches(data_value, value)
            else:
                for data_value in data.values():
                    term_score += self.count_matches(data_value, term)

            if not self.mw.settings[loose_match] and term_score == 0:
                return 0  # If a term did not match any field, we return a score of 0 for the entire entry

            score += term_score

        return score

    def count_matches(self, value, target):
        """
        Count the number of times the target is present in the value or any of its items (if list/dict).
        """
        count = 0

        if isinstance(value, (int, float)):
            if str(value) == target:
                count += 1
        elif isinstance(value, list):
            for item in value:
                count += self.count_matches(item, target)
        elif isinstance(value, dict):
            for item_value in value.values():
                count += self.count_matches(item_value, target)
        elif target.lower() in str(value).lower():
            count += 1

        return count

    def compare_match(self, data_value, compare_term):
        """Match > or < for field searches"""
        operator = compare_term[0]
        target_value = compare_term[1:]

        if isinstance(data_value, (list, dict)):
            value = len(data_value)
        elif isinstance(data_value, (float, int)) or (isinstance(data_value, str) and data_value.isnumeric()):
            value = int(data_value)
        else:
            value = len(str(data_value))

        if target_value and target_value.isnumeric():
            if operator == '>':
                return 1 if value > int(target_value) else 0
            elif operator == '<':
                return 1 if value < int(target_value) else 0

        return 0  # Default case