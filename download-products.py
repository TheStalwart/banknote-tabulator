import requests
import json
import os
import time
from datetime import datetime
import math
from bs4 import BeautifulSoup
import re
import pathlib
from operator import itemgetter
from product import Product
from banknote import Banknote
import sentry_sdk
import sys


# Init Sentry before doing anything that might raise exception
try:
    sentry_sdk.init(
        dsn=pathlib.Path(os.path.join(pathlib.Path(__file__).parent.resolve(), "sentry.dsn")).read_text(),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for tracing.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )
except:
    pass

def report_failure_and_exit():
    if betterstack_heartbeat_url:
        print(f"Reporting heartbeat to {betterstack_heartbeat_url}/fail")
        response = requests.get(f"{betterstack_heartbeat_url}/fail")
        if not response.ok:
            print(f"Failed!")
        print(f"Response: [{response.status_code}]")
    sys.exit(1)

# prevent multiple instances of the script from running at the same time
lock_file_path = os.path.join(pathlib.Path(__file__).parent.resolve(), "download-products.lock")
if os.path.isfile(lock_file_path):
    # if lockfile is older than 24h, recreate it
    if os.path.getmtime(lock_file_path) < time.time() - 60 * 60 * 24:
        os.remove(lock_file_path)
    else:
        print("Another instance of the script is running, exiting")
        report_failure_and_exit()
open(lock_file_path, "w").close()

# Keep cache of entire inventory in RAM
product_index = []

# Define inventory file storage paths
root = pathlib.Path(__file__).parent.resolve()
folder = os.path.join(root, "inventory")
inventory = Banknote(folder)

# Attempt to load Better Stack heartbeat token
betterstack_heartbeat_url = None
try:
    betterstack_heartbeat_url = pathlib.Path(os.path.join(root, "heartbeat.url")).read_text().strip()
except:
    pass

# get delay in seconds from cli options, like "--delay=20", default = 15
delay = 15
for arg in sys.argv:
    if arg.startswith("--delay="):
        delay = int(arg.split("=")[1])

def download_index():
    print("Downloading first page...")
    index_url = 'https://veikals.banknote.lv/lv/filter-products'
    index_params = {'categories_id': 8, 'per_page': 120}
    # https://requests.readthedocs.io/en/latest/user/quickstart/#passing-parameters-in-urls
    r = requests.get(index_url, params={**index_params, 'page': 1})
    first_page = r.json()
    product_index.extend(first_page['data'])

    last_page_number = first_page['last_page']
    print(f"Total amount of pages: {last_page_number}")

    print(f"Downloading page:", end='', flush=True)
    for page_number in range(2, last_page_number+1):
        print(f" #{page_number}", end='', flush=True)
        if delay > 0:
            print(f"... ", end='', flush=True)
            time.sleep(delay)
        r = requests.get(index_url, params={**index_params, 'page': page_number})
        extra_page = r.json()
        product_index.extend(extra_page['data'])
    print(f" DONE!", flush=True)

    # https://www.geeksforgeeks.org/reading-and-writing-json-to-a-file-in-python/
    print(f"Dumping {len(product_index)} products to {inventory.index_file_path}")
    with open(inventory.index_file_path, "w") as index_file:
        json.dump(product_index, index_file, indent=2)
        return os.path.getmtime(inventory.index_file_path)

# Update inventory index if necessary
if not os.path.isfile(inventory.index_file_path):
    index_file_modification_timestamp = download_index()
else:
    try:
        # Check index file age
        INDEX_FILE_MAX_AGE_MINUTES = 55
        index_file_modification_timestamp = os.path.getmtime(inventory.index_file_path)
        current_timestamp = time.time()
        index_file_age_seconds = current_timestamp - index_file_modification_timestamp
        index_file_age_minutes = math.floor(index_file_age_seconds / 60)
        print(f"Index file is {index_file_age_minutes} minutes old")

        if index_file_age_minutes < INDEX_FILE_MAX_AGE_MINUTES:
            print(f"Loading inventory from {inventory.index_file_name}")
            index_file = open(inventory.index_file_path)
            product_index = json.load(index_file)
            print(f"Loaded {len(product_index)} products from {inventory.index_file_path}")
        else:
            index_file_modification_timestamp = download_index()
    except:
        print(f"Failed to parse index file, redownloading")
        index_file_modification_timestamp = download_index()


# Load additional properties absent in index
properties = {}
# If multiple items are added to inventory between downloader executions,
# download item files in the order of "article",
# to avoid listing these items in order reverse of item addition to inventory.
# Unless we sort index before downloading item files,
# order of every batch will be overridden by file modification date.
for item in sorted(product_index, key=itemgetter('article')):
    product = Product(item['id'])
    if len(product.files_downloaded) > 0:
        product.update_last_seen_value()
        item_file_path = product.files_downloaded[-1]
        item_file = open(item_file_path)
        product_properties = json.load(item_file)
        if item['price'] == product_properties['price']:
            # print(f"{item['id']} details already downloaded")
            product_properties['item_file_path'] = item_file_path
            product_properties['item_timestamp'] = product.latest_file_datetime
            properties[item['id']] = product_properties
            continue

    print(f"Downloading details of {item['id']}: {item['title']}")
    product.ensure_path_exists()
    item_file_path = product.create_new_filename()
    print(f"Fetching {item['url']}...")

    if delay > 0:
        print(f"Sleeping for {delay} seconds to avoid blocking")
        time.sleep(delay)

    r = requests.get(item['url'], allow_redirects=False)
    if r.status_code == 301:
        print(f"Redirected to {r.headers['Location']}, removing from index")
        product_index.remove(item)
        continue
    html_contents = r.text
    soup = BeautifulSoup(html_contents, 'html.parser')

    product_data = None

    # Old frontend template (before Oct 9 2024)
    leasing_item = soup.find('product-item-leasing')
    if leasing_item != None and leasing_item.has_attr(':product'):
        product_data = leasing_item[':product']
    else:
        # New frontend template (since Oct 9 2024)
        buy_now_btn = soup.find('buy-now-btn')
        if buy_now_btn == None:
            print(f"Page for {item['id']} has no info, probably sold, removing from index")
            product_index.remove(item)
            continue
        product_data = buy_now_btn[':product']

    if product_data:
        product_properties = json.loads(product_data)
        with open(item_file_path, "w", encoding='utf-8') as item_file:
            json.dump(product_properties, item_file, indent=2)
        product_properties['item_file_path'] = item_file_path
        product_properties['item_timestamp'] = product.latest_file_datetime
        properties[item['id']] = product_properties
        product.update_last_seen_value()
    else:
        print(f"Page of ttem {item['id']} does not contain item information, removing from index")
        product_index.remove(item)


# Normalize data for use in frontend
normalized_inventory = []
for item in product_index:
    n_item = { 'article': item['article'] }
    n_item['id'] = item['id']
    n_item['title'] = item['title']
    n_item['price'] = float(item['price'])

    specs = properties[item['id']]['description_f']
    for entry in specs:
        if re.search('(cpu|proces)', entry['title'], re.IGNORECASE) and (len(entry['value'].strip(' -,')) > 0):
            n_item['cpu'] = entry['value'].strip(' -,')
        if re.search('(ram)', entry['title'], re.IGNORECASE):
            n_item['ram'] = entry['value'].strip()
        if re.search('(atmi|disk|hdd|ssd)', entry['title'], re.IGNORECASE) and not re.search('(oper|las)', entry['title'], re.IGNORECASE):
            # avoid "Diska lasītājs" key
            n_item['storage'] = entry['value'].strip()
        if re.search('(gpu|video)', entry['title'], re.IGNORECASE):
            n_item['gpu'] = entry['value'].strip(' -"')

    address_components = item['branche']['address'].split('<br>')
    if len(address_components) < 2:
        address_components = item['branche']['address'].split(',')

    n_item['city'] = address_components[0].strip(' ,')
    n_item['local_address'] = address_components[1].strip(' ,')

    n_item['url'] = item['url']

    n_item['images'] = []
    for image_data in properties[item['id']]['erp_images']:
        n_item['images'].append(f"https://veikals.banknote.lv/storage/{image_data['path']}")

    n_item['timestamp'] = properties[item['id']]['item_timestamp'].isoformat()

    normalized_inventory.append(n_item)

print(f"Dumping {len(normalized_inventory)} products to {inventory.normalized_file_path}")
inventory_dictionary = {
    'index_file_modification_timestamp': index_file_modification_timestamp,
    'inventory': normalized_inventory,
}
with open(inventory.normalized_file_path, "w", encoding='utf-8') as normalized_file:
    json.dump(inventory_dictionary, normalized_file, indent=2)

inventory.delete_legacy_data()
inventory.prune_products_folder()
inventory.prune_archive_folder()
inventory.archive_inventory()

inventory.print_stats()

os.remove(lock_file_path)

# Report success to Better Stack
if betterstack_heartbeat_url:
    print(f"Reporting heartbeat to {betterstack_heartbeat_url}")
    response = requests.get(betterstack_heartbeat_url)
    if not response.ok:
        print(f"Failed!")
    print(f"Response: [{response.status_code}]")
