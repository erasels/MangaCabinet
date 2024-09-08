import json
import logging
import os
import platform
import subprocess
import sys

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
