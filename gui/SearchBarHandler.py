import json

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem

from gui.Options import search_thrshold, loose_match


class SearchBarHandler:

    def __init__(self, main_window):
        self.mw = main_window
        self.sort_order_reversed = False
        self.showing_all_entries = False
        self.sorting_options = [
            ("By id", lambda entry: entry['id']),
            ("By date added", lambda entry: len(self.mw.data) - self.mw.data.index(entry) - 1),
            ("By Upload", lambda entry: (0 if entry.upload is None else 1, entry.upload_date())),  # Ends up being same as id
            ("By score", lambda entry: entry.get('score', float('-inf')))
        ]
        self.init_ui()

    def init_ui(self):
        # Search bar
        self.mw.search_bar.textChanged.connect(lambda: self.update_list(False))
        self.mw.search_bar.setStyleSheet(self.mw.styles.get("lineedit"))

        # Sorting combo box
        for name, _ in self.sorting_options:
            self.mw.sort_combobox.addItem(name)
        self.mw.sort_combobox.currentIndexChanged.connect(lambda: self.update_list())
        self.mw.sort_combobox.rightClicked.connect(self.toggle_sort_order)
        self.mw.sort_combobox.setStyleSheet(self.mw.styles.get("sorter"))
        self.mw.sort_combobox.setObjectName("Normal")

    def toggle_sort_order(self):
        if self.sort_order_reversed:
            self.mw.sort_combobox.setObjectName("Normal")
        else:
            self.mw.sort_combobox.setObjectName("Reversed")
        self.mw.sort_combobox.setStyleSheet(self.mw.styles["sorter"])  # Refresh the stylesheet to force the update.
        self.sort_order_reversed = not self.sort_order_reversed
        self.update_list()

    def secondary_sort_key(self, x):
        sort_func = self.sorting_options[self.mw.sort_combobox.currentIndex()][1]
        return sort_func(x[0])

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

    def match_score(self, data, terms):
        """Compute a score based on the number of matching terms."""
        score = 0

        for term in terms:
            term_score = 0
            if ":" in term:
                field, value = term.split(":", 1)
                data_value = data.get(field, "")
                term_score = self.count_matches(data_value, value)
            else:
                for data_value in data.values():
                    term_score += self.count_matches(data_value, term)

            if not self.mw.settings[loose_match] and term_score == 0:
                return 0  # If a term did not match any field, we return a score of 0 for the entire entry

            score += term_score

        return score

    def update_list(self, forceRefresh=True):
        search_terms = [term.strip() for term in self.mw.search_bar.text().split(",")]

        # Define sort in case we need it
        _, sort_func = self.sorting_options[self.mw.sort_combobox.currentIndex()]
        selected_group = self.mw.group_combobox.currentData()

        if not selected_group:
            mod_data = self.mw.data
        else:
            # Can be optimized in case update_list gets called a lot
            mod_data = [manga_entry for manga_entry in self.mw.data if manga_entry.group == selected_group]

        # If less than 3 characters and already showing all entries, return early
        if len(self.mw.search_bar.text()) < 3:
            if self.showing_all_entries and not forceRefresh:
                return
            else:
                sorted_data = sorted(mod_data, key=lambda x: sort_func(x), reverse=not self.sort_order_reversed)
                self.mw.list_model.clear()
                for entry in sorted_data:
                    self.create_list_item(entry)
                self.showing_all_entries = True
                return

        # Compute scores for all manga entries and sort them based on the score
        scored_data = [(entry, self.match_score(entry, search_terms)) for entry in mod_data]
        sorted_data = sorted(scored_data, key=lambda x: (-x[1], self.secondary_sort_key(x) * (-1 if not self.sort_order_reversed else 1)))

        self.mw.list_model.clear()  # Clear the list before adding filtered results

        for idx, (entry, score) in enumerate(sorted_data):
            if score > 0 and idx < self.mw.settings[search_thrshold]:
                self.create_list_item(entry)
            else:
                break

        self.showing_all_entries = False

    def create_list_item(self, entry: dict):
        item = QStandardItem()
        item.setData(entry, Qt.UserRole)
        self.mw.list_model.appendRow(item)

