import os
import pathlib
from datetime import datetime
import shutil
import glob
import pytz
import hashlib


class Product:
    FOLDER_NAME = 'products'

    TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
    FILENAME_FORMAT = f"{TIMESTAMP_FORMAT}.json"

    @property
    def inventory_path(self):
        """
        Path of an inventory
        that is a root for specific product data directories
        and index files
        """
        return os.path.join(pathlib.Path(__file__).parent.resolve(), "inventory", self.category_name)

    @property
    def path(self):
        """Path of a specific product data directory"""
        return os.path.join(self.inventory_path, self.FOLDER_NAME, f"{self.id}", '')

    def ensure_path_exists(self):
        if not os.path.isdir(self.path):
            os.mkdir(self.path)

    @property
    def files_downloaded(self):
        """Files in storage for a particular Product. Returns array of absolute paths"""
        def is_not_empty_file(path):
            return os.path.getsize(path) > 0

        return list(sorted(filter(is_not_empty_file, glob.glob(os.path.join(self.path, "*.json")))))

    @property
    def latest_file_datetime(self):
        latest_file_path = self.files_downloaded[-1]
        latest_file_name = os.path.basename(latest_file_path)
        return datetime.strptime(f"{latest_file_name}Z", f"{self.FILENAME_FORMAT}%z")

    def create_new_filename(self):
        """Create filename to dump created/updated product JSON"""
        new_filename = datetime.now().strftime(self.FILENAME_FORMAT)
        print(f"[Product {self.id}]: creating file {new_filename}")
        return os.path.join(self.path, new_filename)

    @property
    def legacy_filename(self):
        return f"{self.id}.json"

    @property
    def legacy_path(self):
        return os.path.join(self.inventory_path, self.legacy_filename)

    def migrate_legacy_data(self):
        # Data scraped from Banknote doesn't contain product creation/update timestamp.
        # Instead, i used file's modification time to add the value to the table.
        # That is very fragile in itself, and i'd like to introduce price history feature later.
        # So we migrate the existing files to store timestamp in a filename.
        legacy_file_timestamp = os.path.getmtime(self.legacy_path)
        legacy_file_datetime = datetime.fromtimestamp(legacy_file_timestamp, tz=pytz.timezone('GMT'))
        migrated_filename = legacy_file_datetime.strftime(self.FILENAME_FORMAT)
        print(f"[Product {self.id}]: migrating legacy file {self.legacy_filename} timestamped {legacy_file_timestamp} to {migrated_filename}")
        migrated_path = os.path.join(self.path, migrated_filename)
        self.ensure_path_exists()
        shutil.move(self.legacy_path, migrated_path)

    def delete_duplicate_data(self):
        """There was a bug earlier that resulted in some product folders
        containing multiple json files with identical data.

        This function deletes duplicate json files keeping only the oldest one.
        """
        checksums = []
        for file_path in self.files_downloaded:
            file_md5 = hashlib.md5(open(file_path,'rb').read()).hexdigest()
            if file_md5 in checksums:
                print(f"[Product {self.id}]: Deleting duplicate data file: {file_path} with MD5 {file_md5}")
                os.remove(file_path)
            else:
                checksums.append(file_md5)

    @property
    def last_seen_file_path(self):
        """Absolute path of file holding last_seen_value"""
        return os.path.join(self.path, "last_seen")

    def update_last_seen_value(self):
        """Update last seen date value in product data folder"""
        value_string = datetime.now().strftime(self.TIMESTAMP_FORMAT)
        # print(f"[Product {self.id}]: Writing value string {value_string} to path {self.last_seen_file_path}")
        with open(self.last_seen_file_path, "w") as last_seen_file:
            last_seen_file.write(value_string)

    def __init__(self, category_name, id):
        self.id = id
        self.category_name = category_name

        if (os.path.isfile(self.legacy_path)) and (os.path.getsize(self.legacy_path) > 0):
            self.migrate_legacy_data()

        self.delete_duplicate_data()


