import logging
import os
import asyncio
import aiohttp
from io import BytesIO

import requests
from PIL import Image, ImageFilter
from PyQt5.QtCore import QObject, pyqtSignal, QThread

from auxillary.DataAccess import MangaEntry


def blur_image(input_path: str, output_path: str):
    # Blurs an image from the given input path and saves the result to the specified output path.
    with Image.open(input_path) as img:
        blurred = img.filter(ImageFilter.GaussianBlur(10))
        blurred.save(output_path)


class ThumbnailManager(QObject):
    BATCH_SIZE = 3
    DELAY = 0.75

    thumbnailDownloaded = pyqtSignal(MangaEntry, str)  # Signal emitted when a thumbnail is downloaded
    startEnsuring = pyqtSignal()

    def __init__(self, data, tags_to_blur):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.data = data
        self.tags_to_blur = tags_to_blur
        self.id_to_path = {}
        self.base_path = os.path.join('assets', 'thumbnails')
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)

        self.worker_thread = QThread()
        self.moveToThread(self.worker_thread)
        self.worker_thread.start()
        self.thumbnailDownloaded.connect(self.log_download)
        self.startEnsuring.connect(self.ensure_all_thumbnails)

    async def ensure_thumbnail(self, manga: MangaEntry):
        # Ensure the thumbnail for the given manga exists, downloading it if necessary.
        if manga.thumbnail_url:
            file_path = os.path.join(self.base_path, manga.id + ".png")
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

    async def batch_ensure_thumbnails(self):
        # Divide data into batches
        total_batches = len(self.data) // self.BATCH_SIZE + (len(self.data) % self.BATCH_SIZE != 0)
        for batch_num in range(total_batches):
            start_idx = batch_num * self.BATCH_SIZE
            end_idx = start_idx + self.BATCH_SIZE

            # Create tasks for the current batch
            tasks = [self.ensure_thumbnail(manga) for manga in self.data[start_idx:end_idx]]

            # Run the tasks for the current batch
            await asyncio.gather(*tasks)

            # Sleep after each batch, but not after the last batch
            if batch_num != total_batches - 1:
                await asyncio.sleep(self.DELAY)

    def ensure_all_thumbnails(self):
        # Preprocess the manga list to filter out those with existing thumbnails
        existing_thumbnails = set(os.listdir(self.base_path))
        new_data = []
        for manga in self.data:
            if (manga.id + ".png") not in existing_thumbnails:
                new_data.append(manga)
            else:
                self.id_to_path[manga.id] = os.path.join(self.base_path, manga.id + ".png")
        self.data = new_data

        if len(self.data) > 0:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.batch_ensure_thumbnails())
            loop.close()
        self.data = None

    def download_thumbnail(self, url, file_path, manga):
        # Download the thumbnail image from the given URL and save it to the specified file path.
        try:
            response = requests.get(url)
            if response.status_code == 200:
                self.save_img(response.content, file_path, manga.id)
            else:
                self.logger.error(f"Couldn't download thumbnail, resp:\n{response}")
        except requests.RequestException as e:
            self.logger.error(f"Error occurred while downloading the thumbnail: {e}")

    def save_img(self, img_data, file_path, manga):
        img = Image.open(BytesIO(img_data))
        if any(tag in manga.tags for tag in self.tags_to_blur):
            img = img.filter(ImageFilter.GaussianBlur(10))
        img.save(file_path)
        self.id_to_path[manga.id] = file_path
        self.thumbnailDownloaded.emit(manga, file_path)

    def log_download(self, manga, file_path):
        self.logger.debug(f"Downloaded thumbnail of {manga.id} - {manga.display_title()}")
