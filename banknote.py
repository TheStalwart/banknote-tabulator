import os
import glob
from datetime import datetime
import pytz
import time


class Banknote:
    """Scrape and normalize inventory of veikals.banknote.lv"""

    @property
    def normalized_file_name(self):
        return 'normalized.json'
    
    @property
    def normalized_file_path(self):
        return os.path.join(self.path, self.normalized_file_name)

    def delete_legacy_data(self):
        """Delete legacy files older than 30 days"""

        glob_pattern = os.path.join(self.path, "[0-9]*.json")
        legacy_file_paths = glob.glob(glob_pattern)
        for legacy_file_path in legacy_file_paths:
            legacy_file_timestamp = os.path.getmtime(legacy_file_path)
            legacy_file_datetime = datetime.fromtimestamp(legacy_file_timestamp, tz=pytz.timezone('GMT'))

            if time.time() - legacy_file_timestamp > 60 * 60 * 24 * 30: # if older than 30 days
                print(f"[Banknote] Deleting legacy file {legacy_file_path} timestamped {legacy_file_datetime}")
                os.remove(legacy_file_path)

    def __init__(self, path):
        self.path = path
