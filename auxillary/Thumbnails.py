import asyncio
import logging
import os
import threading
from io import BytesIO

import aiohttp
import requests
from PIL import Image, ImageFilter
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QPixmap

from auxillary.DataAccess import MangaEntry


def blur_image(input_path: str, output_path: str, blur_strength: int = 10):
    # Blurs an image from the given input path and saves the result to the specified output path.
    with Image.open(input_path) as img:
        blurred = img.filter(ImageFilter.GaussianBlur(blur_strength))
        blurred.save(output_path)


class ThumbnailManager(QObject):
    BATCH_SIZE = 3
    DELAY = 0.75
    DEFAULT_IMG = os.path.join("assets", "images", "no_thumbnail.png")

    thumbnailDownloaded = pyqtSignal(MangaEntry, str)  # Signal emitted when a thumbnail is downloaded
    startEnsuring = pyqtSignal()
    ensureThumbnailsSignal = pyqtSignal(list)

    def __init__(self, mw, data, download, tags_to_blur):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        logging.getLogger('asyncio').setLevel(logging.INFO)
        self.mw = mw
        self.data = data
        self.download = download
        self.tags_to_blur = tags_to_blur
        self.id_to_path = {}
        self.id_to_pixmap = {}
        self.default_img = QPixmap(self.DEFAULT_IMG)
        self.base_path = os.path.join('assets', 'thumbnails')
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

        self.ensureThumbnailsSignal.connect(self.process_entries_for_download)
        self.worker_thread = QThread()
        self.moveToThread(self.worker_thread)
        self.worker_thread.start()
        self.thumbnailDownloaded.connect(self.log_download)
        self.startEnsuring.connect(self.ensure_thumbnails)
        self.mw.dataUpdated.connect(self.ensure_thumbnails)

    async def ensure_thumbnail(self, manga: MangaEntry):
        # Ensure the thumbnail for the given manga exists, downloading it if necessary.
        if manga.thumbnail_url:
            file_path = self.make_file_path(manga)
            await self.async_download_thumbnail(manga, file_path)

    async def async_download_thumbnail(self, manga, file_path):
        # Download the thumbnail image from the given URL and save it to the specified file path.
        async with aiohttp.ClientSession() as session:
            async with session.get(manga.thumbnail_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    self.save_img(image_data, file_path, manga)
                else:
                    self.logger.error(f"Couldn't download thumbnail, resp:\n{response}")

    @pyqtSlot(list)
    def process_entries_for_download(self, entries: list[MangaEntry]):
        """Process entries for downloading thumbnails."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Create and set a new event loop if one doesn't exist
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Check if the loop is running and start it if not
        if not loop.is_running():
            threading.Thread(target=loop.run_forever).start()

            # Schedule the coroutine to be run in the event loop
        asyncio.run_coroutine_threadsafe(self.batch_ensure_thumbnails(entries), loop)

    async def batch_ensure_thumbnails(self, entries):
        # Divide data into batches
        total_batches = len(entries) // self.BATCH_SIZE + (len(entries) % self.BATCH_SIZE != 0)
        for batch_num in range(total_batches):
            start_idx = batch_num * self.BATCH_SIZE
            end_idx = start_idx + self.BATCH_SIZE

            # Create tasks for the current batch
            tasks = [self.ensure_thumbnail(manga) for manga in entries[start_idx:end_idx]]

            # Run the tasks for the current batch
            await asyncio.gather(*tasks)

            # Sleep after each batch, but not after the last batch
            if batch_num != total_batches - 1:
                await asyncio.sleep(self.DELAY)

    def ensure_thumbnails(self, data=None):
        # Preprocess the manga list to filter out those with existing thumbnails
        existing_thumbnails = set(os.listdir(self.base_path))
        new_data = []
        if data is None:
            data = self.data

        for manga in data:
            if (manga.id + ".png") not in existing_thumbnails:
                new_data.append(manga)
            else:
                self.id_to_path[manga.id] = os.path.join(self.base_path, manga.id + ".png")

        if len(new_data) > 0 and self.download:
            self.ensureThumbnailsSignal.emit(new_data)

    def download_thumbnail(self, url, file_path, manga):
        # Download the thumbnail image from the given URL and save it to the specified file path.
        try:
            response = requests.get(url)
            if response.status_code == 200:
                self.save_img(response.content, file_path, manga, autoBlur=False)
            else:
                self.logger.error(f"Couldn't download thumbnail, resp:\n{response}")
        except requests.RequestException as e:
            self.logger.error(f"Error occurred while downloading the thumbnail: {e}")

    def save_img(self, img_data, file_path, manga, max_size=400, autoBlur=True):
        img = Image.open(BytesIO(img_data))
        if autoBlur and any(tag in manga.tags for tag in self.tags_to_blur):
            img = img.filter(ImageFilter.GaussianBlur(10))
        # Resize the image if it exceeds the max_size while maintaining aspect ratio
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size))
        img.save(file_path)
        self.update_thumbnail(manga.id, file_path)
        self.thumbnailDownloaded.emit(manga, file_path)

    def log_download(self, manga, file_path):
        self.logger.debug(f"Downloaded thumbnail of {manga.id} - {manga.display_title()}")

    def get_thumbnail_path(self, id):
        return self.id_to_path.get(id)

    def get_thumbnail(self, id):
        img = self.id_to_pixmap.get(id)
        if not img:
            path = self.get_thumbnail_path(id)
            if path:
                img = QPixmap(path)
                self.id_to_pixmap[id] = img
            else:
                img = self.default_img
                self.id_to_pixmap[id] = self.default_img
        return img

    def update_thumbnail(self, id, path):
        """Updates the references when an image is created on disk."""
        self.id_to_path[id] = path
        self.id_to_pixmap[id] = QPixmap(path)

    def make_file_path(self, manga):
        return os.path.join(self.base_path, manga.id + ".png")

    def stop(self):
        """Called when the application closes to prevent memory leaks"""
        if self.worker_thread.isRunning():
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(loop.stop)
            self.worker_thread.quit()
            self.worker_thread.wait()
