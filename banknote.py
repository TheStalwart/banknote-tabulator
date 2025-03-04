import os
import glob
from datetime import datetime
import pytz
import time
import zipfile
import shutil
from product import Product


class Banknote:
    """Scrape and normalize inventory of veikals.banknote.lv"""

    @property
    def index_file_name(self):
        return 'index.json'

    @property
    def index_file_path(self):
        return os.path.join(self.path, self.index_file_name)

    @property
    def normalized_file_name(self):
        return 'normalized.json'

    @property
    def normalized_file_path(self):
        return os.path.join(self.path, self.normalized_file_name)

    @property
    def archives_path(self):
        return os.path.join(self.path, 'archives')

    @property
    def archive_count(self):
        """The amount of archive files in archives_path

        Counts both timestamped archives,
        e.g. "archives/2024-03-26_09-35-21.zip",
        and "archives/latest.zip"
        """
        return len(list(glob.glob(os.path.join(self.archives_path, "[0-9l]*.zip"))))

    @property
    def product_root(self):
        return os.path.join(self.path, Product.FOLDER_NAME)

    @property
    def product_cache_count(self):
        """Count product cache folders downloaded"""
        return len(list(glob.glob(os.path.join(self.product_root, "[0-9]*"))))

    def archive_inventory(self):
        """Create new zip archive with contents of inventory"""
        new_zipfile_name = 'new.zip'
        new_zipfile_path = os.path.join(self.archives_path, new_zipfile_name)

        # Remove any unfinished zipfiles from previous executions
        if os.path.isfile(new_zipfile_path):
            print(f"{self.log_tag} Found questionable {new_zipfile_path}, deleting")
            os.remove(new_zipfile_path)

        # Create new zipfile
        with zipfile.ZipFile(new_zipfile_path, 'w', zipfile.ZIP_DEFLATED) as new_zipfile:
            new_zipfile.write(self.index_file_path, self.index_file_name)
            new_zipfile.write(self.normalized_file_path, self.normalized_file_name)
            product_paths = list(glob.glob(os.path.join(self.product_root, "[0-9]*")))
            for product_path in product_paths:
                product_file_paths = list(glob.glob(os.path.join(product_path, '*.json')))
                for product_file_path in product_file_paths:
                    new_zipfile.write(product_file_path, os.path.relpath(product_file_path, self.path))

        # Rename latest to timestamped
        latest_zipfile_name = 'latest.zip'
        latest_zipfile_path = os.path.join(self.archives_path, latest_zipfile_name)
        if os.path.isfile(latest_zipfile_path):
            latest_zipfile_timestamp = os.path.getmtime(latest_zipfile_path)
            latest_zipfile_datetime = datetime.fromtimestamp(latest_zipfile_timestamp, tz=pytz.timezone('GMT'))
            timestamped_zipfile_name = latest_zipfile_datetime.strftime(f"{Product.TIMESTAMP_FORMAT}.zip")
            timestamped_zipfile_path = os.path.join(self.archives_path, timestamped_zipfile_name)
            print(f"{self.log_tag} Found {latest_zipfile_path}, moving to {timestamped_zipfile_path}")
            shutil.move(latest_zipfile_path, timestamped_zipfile_path)

        # Rename new to latest
        print(f"{self.log_tag} Moving {new_zipfile_path} to {latest_zipfile_path}")
        shutil.move(new_zipfile_path, latest_zipfile_path)

    def delete_legacy_data(self):
        """Delete legacy files older than 30 days"""

        glob_pattern = os.path.join(self.path, "[0-9]*.json")
        legacy_file_paths = glob.glob(glob_pattern)
        for legacy_file_path in legacy_file_paths:
            legacy_file_timestamp = os.path.getmtime(legacy_file_path)
            legacy_file_datetime = datetime.fromtimestamp(legacy_file_timestamp, tz=pytz.timezone('GMT'))

            if time.time() - legacy_file_timestamp > 60 * 60 * 24 * 30: # if older than 30 days
                print(f"{self.log_tag} Deleting legacy file {legacy_file_path} timestamped {legacy_file_datetime}")
                os.remove(legacy_file_path)

    def prune_archive_folder(self):
        """Delete older archives to limit disk space they are taking"""
        archive_size_cap_mb = 2048 # 2 GB
        glob_pattern = os.path.join(self.archives_path, "[0-9]*.zip")
        archive_file_paths = sorted(glob.glob(glob_pattern))

        # https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python
        while sum(os.path.getsize(f) for f in archive_file_paths) / 1024 / 1024 > archive_size_cap_mb:
            victim_path = archive_file_paths.pop(0)
            print(f"{self.log_tag} Total archive size exceeds {archive_size_cap_mb} MB, deleting {victim_path}")
            os.remove(victim_path)

    def prune_products_folder(self):
        """Delete data of products with unknown last_seen value"""
        product_folders_deleted = 0
        product_paths = list(glob.glob(os.path.join(self.product_root, "[0-9]*")))
        for product_path in product_paths:
            last_seen_path = os.path.join(product_path, "last_seen")
            if not os.path.isfile(last_seen_path):
                product_folders_deleted += 1
                print(f"{self.log_tag} Found product data folder {product_path} with no last_seen file, deleting")
                shutil.rmtree(product_path)
        if product_folders_deleted > 0:
            print(f"{self.log_tag} Total product data folders with no last_seen file deleted: {product_folders_deleted}")

    def print_stats(self):
        """Print various stats and indicators about inventory"""
        print(f"{self.log_tag} Total items in product cache: {self.product_cache_count}")
        print(f"{self.log_tag} Total archives: {self.archive_count}")

    def __init__(self, path, category_name):
        self.path = os.path.join(path, category_name)
        self.log_tag = '[Banknote/{}]'.format(category_name)
        self.category_name = category_name
