import json
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

from gui.Options import default_manga_loc

logger = logging.getLogger(__name__)


class DiskHandler:
    def __init__(self, mw):
        self.mw = mw
        self.default_script_location = mw.open_on_disk_script

    def open(self, entry, script_location=None):
        if script_location or bool(self.default_script_location):
            return self.open_with_script(entry, script_location, direct_call=False)
        else:
            return self.open_in_explorer(entry, direct_call=False)

    def open_in_explorer(self, entry, direct_call=True):
        folder_path = self.check_disk_location(entry, direct_call)
        if not folder_path:
            return False

        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux and others
                subprocess.run(["xdg-open", folder_path])
            self.update_num_opens(entry)
        except Exception as e:
            logger.error(f"Failed to open folder for {entry.id}: {folder_path}\nException: {e}")
            return False
        return True

    def open_with_script(self, entry, script_location=None, direct_call=True):
        if not self.check_disk_location(entry, direct_call):
            return False

        script_location = script_location or self.default_script_location

        if not os.path.exists(script_location):
            if direct_call:
                logger.warning(f"Script doesn't exist: {script_location}")
            return False

        entry_json = json.dumps(entry)  # Convert entry to pass it
        try:
            subprocess.run([sys.executable, script_location, entry_json], check=True)
            self.update_num_opens(entry)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to execute script for {entry.id}: {e}")
            return False
        return True

    def check_disk_location(self, entry, should_log_failure=True):
        folder_path = entry.disk_location(loose_check=False)
        if not folder_path:
            if should_log_failure:
                logger.warning(f"Tried opening path that doesn't exist for {entry.id}: {folder_path}")
            return None
        else:
            return folder_path

    def update_num_opens(self, entry):
        # TODO: Streamline save system, shares code with open_tab_from_index
        entry.opens += 1
        logger.debug(f"{entry.id}: MC_num_opens was updated with: {entry.opens}")
        entry.update_last_opened()
        # entry.update_last_edited()  # Doesn't feel like it should be updated here
        self.mw.is_data_modified = True

    def check_entry_disk_location(self, entry, loose_check=False):
        # If entry doesn't have a defined filesystem location and default is defined, try to find it
        if self.mw.settings[default_manga_loc] and not entry.disk_location(loose_check=loose_check):
            # Special handling for path here because I want to prevent backslash usage in data json
            entry_path = Path(self.mw.settings[default_manga_loc]) / entry.id
            if entry_path.exists():
                # TODO: Streamline save system
                entry.filesystem_location = str(entry_path).replace('\\', '/')
                self.mw.is_data_modified = True
                entry.update_last_edited()
                logger.debug(f"{entry.id}: filesystem_location was updated with: {entry.filesystem_location}")

    def check_entries_disk_locations(self, entries, loose_check=True):
        """
        Efficiently checks and updates filesystem locations for multiple entries
        by minimizing disk I/O with a single directory read.
        """
        if not self.mw.settings[default_manga_loc]:
            return
        manga_loc_path = Path(self.mw.settings[default_manga_loc])

        existing_paths = os.listdir(manga_loc_path)

        # Iterate through each entry in the provided list
        for entry in entries:
            cur_loc = entry.filesystem_location
            cur_loc_path = Path(cur_loc) if cur_loc else None

            if loose_check:
                # Catches location not written or written but id changed mostly
                check_condition = (not cur_loc_path or
                                   (cur_loc_path.is_relative_to(manga_loc_path) and
                                    cur_loc_path.name not in existing_paths))
            else:
                # Catches not written or not existing (does an IO operation, costly, only done rarely)
                check_condition = (not cur_loc_path or not cur_loc_path.exists())

            if check_condition:
                # Construct the path for the entry
                entry_path = manga_loc_path / entry.id

                if entry_path.name in existing_paths:
                    # TODO: Streamline save system
                    entry.filesystem_location = str(entry_path).replace('\\', '/')
                    self.mw.is_data_modified = True
                    entry.update_last_edited()
                    logger.debug(f"{entry.id}: filesystem_location was updated with: {entry.filesystem_location}")
