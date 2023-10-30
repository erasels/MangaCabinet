import logging
import webbrowser

from auxillary.DataAccess import MangaEntry

logger = logging.getLogger(__name__)


class BrowserHandler:
    def __init__(self, main_window):
        self.mw = main_window
        self.browser = None
        self.unsupported, self.use_default = False, False
        self.browser_path = self.mw.browser_path
        self.browser_flags = self.mw.browser_flags
        self.default_URL = self.mw.default_URL

        if self.browser_path:
            formatted_flags = " ".join(["-" + flag for flag in self.browser_flags])
            browser_command = f"{self.browser_path} {formatted_flags} %s"
            self.browser = webbrowser.get(browser_command)
        else:
            if not self.default_URL:
                self.unsupported = True
                logger.warning("Missing browser path and default URL, no support for opening in browser.")
            else:
                self.use_default = True
                logger.info("Missing browser path, will use defaults.")

    def open_tab(self, value):
        if self.unsupported:
            return
        if isinstance(value, MangaEntry):
            self._handle_manga_entry(value)
        elif isinstance(value, str):
            self._handle_url(value)
        else:
            raise ValueError("Unsupported type for open_tab")

    def _handle_manga_entry(self, entry):
        if entry.open_url:
            self._handle_url(entry.open_url)
        else:
            self._handle_url(self.default_URL + entry.id)

    def _handle_url(self, url):
        if self.use_default:
            webbrowser.open_new_tab(url)
        else:
            self.browser.open_new_tab(url)
