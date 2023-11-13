import os
import random
import re
from collections import defaultdict
from typing import Tuple, Callable, Any, List

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QLineEdit, QLabel, QHBoxLayout, QPushButton, QCompleter

from auxillary.DataAccess import MangaEntry
from gui.WidgetDerivatives import RightClickableComboBox
from gui.Options import search_thrshold, loose_match, multi_match, show_removed, default_sort


class SearchBarHandler:
    RESELECT_DELAY = 25

    def __init__(self, main_window):
        self.random_button = None
        self.sort_combobox = None
        self.hits_label = None
        self.search_bar = None
        self.mw = main_window
        self.sort_order_reversed = False
        self.showing_all_entries = False
        self.sorting_options = [
            # Name, algorithm, should be reversed by default
            ("By data order", lambda entry: self.mw.entry_to_index.get(entry.id, 0), False),
            ("By id", lambda entry: (0, int(entry.id)) if entry.id.isdigit() else (1, entry.id), True),  # number id or UUID
            ("By upload date", lambda entry: (0 if entry.upload is None else 1, entry.upload_date()), True),
            ("By name", lambda entry: entry.display_title().lower(), False),
            ("By artist", lambda entry: entry.first_artist().lower(), False),
            ("By score", lambda entry: entry.get('score', float('-inf')), True)  # Reversed will show unrated first
        ]
        self.init_ui()

    def init_ui(self):
        # Search bar
        self.search_bar = QLineEdit(self.mw)
        self.search_bar.setStyleSheet(self.mw.styles.get("lineedit"))
        self.search_bar.setPlaceholderText("Search...")
        completer = FieldSearchCompleter([field+":" for field in self.mw.common_attributes], self.search_bar)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.search_bar.setCompleter(completer)

        # Create a timer with an interval of 150 milliseconds
        self.search_timer = QTimer(self.mw)
        self.search_timer.setSingleShot(True)  # Ensure the timer only triggers once
        self.search_timer.timeout.connect(lambda: self.update_list(False))

        # Connect textChanged signal to restart the timer
        self.search_bar.textChanged.connect(self.reset_search_timer)

        # Hits label
        self.hits_label = QLabel(self.mw)
        self.hits_label.hide()

        # Sorting combo box
        self.sort_combobox = RightClickableComboBox()
        for name, _, _ in self.sorting_options:
            self.sort_combobox.addItem(name)
        default_sort_index = next((i for i, (name, _, _) in enumerate(self.sorting_options) if name == self.mw.settings[default_sort]), 0)
        self.sort_combobox.setCurrentIndex(default_sort_index)
        self.sort_combobox.currentIndexChanged.connect(lambda: self.update_list())
        self.sort_combobox.rightClicked.connect(self.toggle_sort_order)
        self.sort_combobox.setStyleSheet(self.mw.styles.get("sorter"))
        self.sort_combobox.setObjectName("Normal")

        # Random button
        self.random_button = QPushButton("Random", self.mw)
        self.random_button.clicked.connect(self.get_random_item)
        self.random_button.setStyleSheet(self.mw.styles.get("textbutton"))

    def get_layout(self, widgets):
        search_box = QHBoxLayout()  # Create a horizontal box layout
        search_box.addWidget(self.search_bar, 1)  # The '1' makes the search bar expand to fill available space
        search_box.addWidget(self.hits_label)
        search_box.addWidget(self.sort_combobox)
        search_box.addWidget(self.random_button)
        for widget in widgets:
            search_box.addWidget(widget)
        return search_box

    def reset_search_timer(self):
        # Restart the timer every time this method is called
        self.search_timer.stop()
        self.search_timer.start(150)

    def get_random_item(self):
        total_items = self.mw.manga_list_handler.list_model.rowCount()
        if total_items <= 1:
            return

        current_index = self.mw.manga_list_handler.list_view.currentIndex().row()
        random_index = random.randint(0, total_items - 1)
        while random_index == current_index:
            random_index = random.randint(0, total_items - 1)
        index = self.mw.manga_list_handler.list_model.index(random_index, 0)

        self.mw.manga_list_handler.select_index(index, True)

    def toggle_sort_order(self):
        if self.sort_order_reversed:
            self.sort_combobox.setObjectName("Normal")
        else:
            self.sort_combobox.setObjectName("Reversed")
        self.sort_combobox.setStyleSheet(self.mw.styles["sorter"])  # Refresh the stylesheet to force the update.
        self.sort_order_reversed = not self.sort_order_reversed
        self.update_list()

    def apply_filters(self, entry, filters):
        # Apply all filters; if any filter returns False, the entry is excluded
        return all(filter_func(entry) for filter_func in filters)

    def update_list(self, forceRefresh=True):
        search_terms = [term.strip() for term in self.search_bar.text().split(",")]

        # Define sort in case we need it
        sorting_option: tuple[str, Callable, bool] = self.sorting_options[self.sort_combobox.currentIndex()]
        reverse_final = sorting_option[2] ^ self.sort_order_reversed  # XOR
        selected_group = self.mw.group_handler.group_combobox.currentData()

        # Aggregate applicable filters
        filters = []
        if selected_group:
            filters.append(lambda e: e.group == selected_group)
        if not self.mw.settings[show_removed]:
            filters.append(lambda e: not e.removed)

        # Now filter the data using a single list comprehension
        if filters:
            mod_data = [entry for entry in self.mw.data if self.apply_filters(entry, filters)]
        else:
            mod_data = self.mw.data

        # If less than 3 characters and already showing all entries, return early
        if len(self.search_bar.text()) < 3:
            if self.showing_all_entries and not forceRefresh:
                return
            else:
                sorted_data = sorted(mod_data, key=lambda x: sorting_option[1](x), reverse=reverse_final)
                self.readd_items(sorted_data)
                self.showing_all_entries = True
                self.hits_label.hide()
                return

        # Compute scores for all manga entries and sort them based on the score
        scored_data = [(entry, self.match_score(entry, search_terms)) for entry in mod_data]
        grouped_data = defaultdict(list)
        for entry, score in scored_data:
            if score != 0:  # prune non-hits early
                grouped_data[score].append((entry, score))

        # 2. Sort Each Group by Secondary Key
        for score, group in grouped_data.items():
            grouped_data[score] = sorted(group, key=lambda x: sorting_option[1](x[0]), reverse=reverse_final)

        sorted_data = [item for score in sorted(grouped_data.keys(), reverse=True) for item in grouped_data[score]]
        hit_count = len(sorted_data)
        threshold = self.mw.settings[search_thrshold]

        if threshold == 0:
            entries_to_add = [entry for entry, _ in sorted_data]
        else:
            entries_to_add = [entry for entry, _ in sorted_data[:threshold]]
        self.readd_items(entries_to_add)

        if hit_count > 0 and search_terms:
            self.hits_label.setText(f"Hits: {hit_count}")
            self.hits_label.show()
        else:
            self.hits_label.hide()

        self.showing_all_entries = False

    def lists_match(self, new_data):
        """ Check if the current list_view data matches the new data set."""
        if self.mw.manga_list_handler.list_model.rowCount() != len(new_data):
            return False

        for row in range(self.mw.manga_list_handler.list_model.rowCount()):
            item = self.mw.manga_list_handler.list_model.item(row)
            if item.data(Qt.UserRole) != new_data[row]:
                return False

        return True

    def readd_items(self, new_data):
        """Add items to list_view and reselect last entry in case lists changed."""
        if not self.lists_match(new_data):
            entry = self.mw.details_handler.cur_data
            self.mw.manga_list_handler.add_items(new_data)
            if entry:
                self.mw.manga_list_handler.select_index_by_id(entry.id, notify_on_failure=False)
            QTimer.singleShot(self.RESELECT_DELAY, self.mw.manga_list_handler.rescroll)
        else:
            # Added to instantly refresh entry if it was modified without changing order
            self.mw.manga_list_handler.list_view.viewport().update()

    def match_score(self, data, terms):
        """Compute a score based on the number of matching terms."""
        score = 0

        for term in terms:
            term_score = 0
            if ":" in term:
                field, value = term.split(":", 1)
                fields_to_search = MangaEntry.FIELD_ALIASES_AND_GROUPING.get(field, [field])

                for search_field in fields_to_search:
                    data_value = data.get(search_field, "")
                    if value and value[0] in [">", "<"]:
                        term_score += self.compare_match(data_value, value)
                    else:
                        term_score += self.count_matches(data_value, value)
            else:
                for data_value in data.values():
                    term_score += self.count_matches(data_value, term)

            if not self.mw.settings[loose_match] and term_score == 0:
                return 0  # If a term did not match any field, we return a score of 0 for the entire entry

            score += term_score

        if not self.mw.settings[multi_match] and score > 1:
            score = 1  # Disable multiple match weighting to preserve proper sort order

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

        return 0


class FieldSearchCompleter(QCompleter):
    def pathFromIndex(self, index):
        # Get the completion string from the index
        completion = super().pathFromIndex(index)
        # Get the text in the widget to the last comma
        text = self.widget().text()
        index = text.rfind(",")
        if index != -1:
            text = text[:index+1]
        else:
            text = ""
        # Add completion to old text
        return text + completion

    def splitPath(self, path):
        # Split the path at the last comma or space to find the prefix
        last_comma = path.rfind(',')
        if last_comma == -1:
            return [path.strip()]
        else:
            return [path[last_comma + 1:].strip()]
