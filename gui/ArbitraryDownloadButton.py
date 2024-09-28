import json
import logging
import os
import subprocess

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QPushButton, QDialog, QVBoxLayout, QLineEdit, QLabel, QFileDialog, QHBoxLayout

from auxillary.DataAccess import MangaEntry
from auxillary.JSONMethods import save_json
from gui import Options

logger = logging.getLogger(__name__)


class ArbitraryDownloadButton(QPushButton):
    def __init__(self, parent=None):
        super(ArbitraryDownloadButton, self).__init__(parent)
        self.mw = parent
        self.setIcon(QIcon(os.path.join(self.mw.image_path, 'download_icon.png')))
        self.setIconSize(QSize(24, 24))
        self.setFixedSize(24, 24)  # Set the button size to match the icon size
        self.setStyleSheet("""ArbitraryDownloadButton { border: none; }
                    ArbitraryDownloadButton:hover { background-color: #cccccc; border-radius: 5px;}""")
        self.clicked.connect(self.openDialog)
        self.setToolTip("Entry Download Scripts")

    def openDialog(self):
        dialog = ScriptDialog(self.mw, self)
        dialog.exec_()


class ScriptDialog(QDialog):
    def __init__(self, mw, parent=None):
        super(ScriptDialog, self).__init__(parent)
        self.setWindowTitle("Download Manga")
        self.mw = mw
        self.scriptPath = self.mw.settings.get(Options.download_script_loc, os.path.join('auxillary', 'EmptyMangaGenerator.py'))
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Label for the current script location
        self.locationLabel = QLabel(f"Current script location:\n{self.scriptPath}", self)
        layout.addWidget(self.locationLabel)

        inputLabel = QLabel("Input for the script:", self)
        layout.addWidget(inputLabel)

        self.lineEdit = QLineEdit(self)
        self.lineEdit.setStyleSheet(self.mw.styles.get("lineedit"))
        self.lineEdit.setPlaceholderText("Input will be sent to the script")
        layout.addWidget(self.lineEdit)

        # Horizontal layout for buttons
        buttonLayout = QHBoxLayout()

        executeButton = QPushButton('Execute', self)
        executeButton.setStyleSheet(self.mw.styles.get("textbutton"))
        executeButton.clicked.connect(self.executeScript)
        buttonLayout.addWidget(executeButton)

        loadButton = QPushButton('Select script', self)
        loadButton.setStyleSheet(self.mw.styles.get("textbutton"))
        loadButton.clicked.connect(self.loadScript)
        buttonLayout.addWidget(loadButton)

        layout.addLayout(buttonLayout)

        noteLabel = QLabel("NOTE: Selected script should provide a list of dicts or dict output by printing them.", self)
        layout.addWidget(noteLabel)

    def loadScript(self):
        location = self.mw.settings.get(Options.download_script_loc, "")
        newScriptPath, _ = QFileDialog.getOpenFileName(self, "Open Python script", location, "Python Files (*.py)")
        if newScriptPath:
            self.scriptPath = newScriptPath
            # Save new path
            if self.scriptPath != location:
                self.mw.settings[Options.download_script_loc] = self.scriptPath
                save_json(self.mw.settings_file, self.mw.settings)

            # Update location label
            self.locationLabel.setText(f"Current script location:\n{self.scriptPath}")

    def executeScript(self):
        if self.scriptPath:
            try:
                # Running the script as a subprocess
                logger.info(f"Executing {self.scriptPath}\nWith input: {self.lineEdit.text()}")
                result = subprocess.run(['python', self.scriptPath, self.lineEdit.text()], capture_output=True, text=True, check=True)
                self.retrieve_output(result.stdout)
                self.accept()
            except subprocess.CalledProcessError as e:
                logger.error(f"Error executing script: {e}")
                self.mw.toast.show_notification(f"Error when executing script:\n{e}")
        else:
            self.mw.toast.show_notification("Cannot download item due to no script being selected.")

    def retrieve_output(self, output: str):
        try:
            output_struct = json.loads(output)
            logger.debug(f"Retrieving output from subprocess:\n{output_struct}")

            new_data = []
            if isinstance(output_struct, dict):
                new_data.append(self.check_dict(output_struct))
            elif isinstance(output_struct, list):
                new_data.extend(self.check_dict(item) for item in output_struct if isinstance(item, dict))

            new_data = [data for data in new_data if data]
            if new_data:
                self.mw.addNewData(new_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON output: {e}")
        except Exception as e:
            logger.error(f"Error processing output: {e}")

    def check_dict(self, data: dict):
        id = data.get("id", None)
        if id and id not in self.mw.entry_to_index.keys():
            return MangaEntry(data)

        logger.warning(f"Could not add manga because it had no id or the id was already in data.\nData: {data}")
        return None
