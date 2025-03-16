import glob
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
import shutil
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

# Attempt to load Better Stack heartbeat token
betterstack_heartbeat_url = None
try:
    betterstack_heartbeat_url = pathlib.Path(os.path.join(pathlib.Path(__file__).parent.resolve(), "heartbeat.url")).read_text().strip()
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

known_categories = [
    {
        'name': 'laptops',
        'id': 8,
    },
    {
        'name': 'monitors',
        'id': 11,
    }
]

def normalize_product(category_name, specs):
    normalized = {}
    for entry in specs:
        entry['value'] = entry['value'].replace('\n', '').replace('\t', '').replace('&nbsp;', ' ')
        if category_name == 'laptops':
            if re.search('(cpu|proces)', entry['title'], re.IGNORECASE) and (len(entry['value'].strip(' -,')) > 0):
                normalized['cpu'] = entry['value'].strip(' -,')
            elif re.search('(ram)', entry['title'], re.IGNORECASE):
                normalized['ram'] = entry['value'].strip()
            elif re.search('(atmi|disk|hdd|ssd)', entry['title'], re.IGNORECASE) and not re.search('(oper|las)', entry['title'], re.IGNORECASE):
                # avoid "Diska lasītājs" key
                normalized['storage'] = entry['value'].strip()
            elif re.search('(gpu|video)', entry['title'], re.IGNORECASE):
                normalized['gpu'] = entry['value'].strip(' -"')
        elif category_name == 'monitors':
            if re.search('(izšķirtspēja)', entry['title'], re.IGNORECASE) and (len(entry['value'].strip(' ')) > 0):
                normalized['resolution'] = entry['value'].replace(' x ', 'x').strip(' ')
            elif re.search('(izmērs)', entry['title'], re.IGNORECASE) and (len(entry['value'].strip(' ')) > 0):
                normalized['size'] = entry['value'].strip(' ')
            elif re.search('(frekvence)', entry['title'], re.IGNORECASE) and (len(entry['value'].strip(' ')) > 0):
                normalized['refresh_rate'] = entry['value'].strip(' ')
            elif re.search('(tips)', entry['title'], re.IGNORECASE) and (len(entry['value'].strip(' ')) > 0):
                normalized['panel'] = entry['value'].strip(' ')
    return normalized

# get cli options: --delay=15 in seconds; --categories=laptops,monitors
delay = 15
categories_to_fetch = ["laptops", "monitors"]
for arg in sys.argv:
    if arg.startswith("--delay="):
        delay = int(arg.split("=")[1])
    elif arg.startswith("--categories="):
        categories_to_fetch = arg.split("=")[1].split(",")

for category in categories_to_fetch:
    if not any(c['name'] == category for c in known_categories):
        print(f"Unknown category: {category}")
        report_failure_and_exit()

# prevent multiple instances of the script from running at the same time, scoped by categories
lock_file_path = os.path.join(pathlib.Path(__file__).parent.resolve(), "download-products_{}.lock".format("_".join(categories_to_fetch)))
if os.path.isfile(lock_file_path):
    # if lockfile is older than 24h, recreate it
    if os.path.getmtime(lock_file_path) < time.time() - 60 * 60 * 24:
        os.remove(lock_file_path)
    else:
        print("Another instance of the script is running, exiting")
        report_failure_and_exit()
open(lock_file_path, "w").close()

for category in known_categories:
    os.makedirs(os.path.join(pathlib.Path(__file__).parent.resolve(), "inventory", category['name'], "archives"), exist_ok=True)
    os.makedirs(os.path.join(pathlib.Path(__file__).parent.resolve(), "inventory", category['name'], "products"), exist_ok=True)

# Define inventory file storage paths
root = pathlib.Path(__file__).parent.resolve()
folder = os.path.join(root, "inventory")
inventories = []
for category in categories_to_fetch:
    inventories.append(Banknote(folder, category))

# TODO: Remove this migration code after the first prod deployment
# If there's no inventory/laptops/index.json dir, migrate from the legacy structure, assuming the old data is only about laptops
first_category_name = known_categories[0]['name']
if not os.path.isfile(os.path.join(folder, first_category_name, "index.json")):
    print("Migrating legacy data, if any, to the new structure")
    for archive_file in glob.glob(os.path.join(folder, "archives", "*.zip")):
        new_file_name = os.path.join(folder, first_category_name, "archives", os.path.basename(archive_file))
        print(f"Moving {archive_file} to {new_file_name}")
        shutil.move(archive_file, os.path.join(folder, first_category_name, "archives", os.path.basename(archive_file)))
    for product_dir in glob.glob(os.path.join(folder, Product.FOLDER_NAME, "*")):
        if os.path.isdir(product_dir):
            new_dir_name = os.path.join(folder, first_category_name, Product.FOLDER_NAME, os.path.basename(product_dir))
            print(f"Moving {product_dir} to {new_dir_name}")
            shutil.move(product_dir, new_dir_name)
    print("Migration done")

def download_index(inventory):
    log_tag = "[DL/{}]".format(inventory.category_name)
    product_index = []

    print(f"{log_tag} Downloading first page...")
    index_url = 'https://veikals.banknote.lv/lv/filter-products'
    category_id = next(c['id'] for c in known_categories if c['name'] == inventory.category_name)
    index_params = {'categories_id': category_id, 'per_page': 120}
    # https://requests.readthedocs.io/en/latest/user/quickstart/#passing-parameters-in-urls
    r = requests.get(index_url, params={**index_params, 'page': 1})
    first_page = r.json()
    product_index.extend(first_page['data'])

    last_page_number = first_page['last_page']
    print(f"{log_tag} Total amount of pages: {last_page_number}")

    print(f"{log_tag} Downloading page:", end='', flush=True)
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
    print(f"{log_tag} Dumping {len(product_index)} products to {inventory.index_file_path}")
    with open(inventory.index_file_path, "w") as index_file:
        json.dump(product_index, index_file, indent=2)
    return product_index, os.path.getmtime(inventory.index_file_path)

for inventory in inventories:
    # Keep cache of entire category inventory in RAM
    product_index = []
    log_tag = "[Load/{}]".format(inventory.category_name)

    # Update inventory index if necessary
    if not os.path.isfile(inventory.index_file_path):
        product_index, index_file_modification_timestamp = download_index(inventory)
    else:
        try:
            # Check index file age
            INDEX_FILE_MAX_AGE_MINUTES = 55
            index_file_modification_timestamp = os.path.getmtime(inventory.index_file_path)
            current_timestamp = time.time()
            index_file_age_seconds = current_timestamp - index_file_modification_timestamp
            index_file_age_minutes = math.floor(index_file_age_seconds / 60)
            print(f"{log_tag} Index file is {index_file_age_minutes} minutes old")

            if index_file_age_minutes < INDEX_FILE_MAX_AGE_MINUTES:
                print(f"{log_tag} Loading inventory from {inventory.index_file_name}")
                index_file = open(inventory.index_file_path)
                product_index = json.load(index_file)
                print(f"{log_tag} Loaded {len(product_index)} products from {inventory.index_file_path}")
            else:
                product_index, index_file_modification_timestamp = download_index(inventory)
        except:
            print(f"{log_tag} Failed to parse index file, redownloading")
            product_index, index_file_modification_timestamp = download_index(inventory)


    # Load additional properties absent in index
    properties = {}
    # If multiple items are added to inventory between downloader executions,
    # download item files in the order of "article",
    # to avoid listing these items in order reverse of item addition to inventory.
    # Unless we sort index before downloading item files,
    # order of every batch will be overridden by file modification date.
    for item in sorted(product_index, key=itemgetter('article')):
        product = Product(inventory.category_name, item['id'])
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

        print(f"{log_tag} Downloading details of {item['id']}: {item['title']}")
        product.ensure_path_exists()
        item_file_path = product.create_new_filename()
        print(f"{log_tag} Fetching {item['url']}...")

        if delay > 0:
            print(f"{log_tag} Sleeping for {delay} seconds to avoid blocking")
            time.sleep(delay)

        r = requests.get(item['url'], allow_redirects=False)
        if r.status_code == 301:
            print(f"{log_tag} Redirected to {r.headers['Location']}, removing from index")
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
                print(f"{log_tag} Page for {item['id']} has no info, probably sold, removing from index")
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
            print(f"{log_tag} Page of ttem {item['id']} does not contain item information, removing from index")
            product_index.remove(item)


    # Normalize data for use in frontend
    normalized_inventory = []
    for item in product_index:
        n_item = { 'article': item['article'] }
        n_item['id'] = item['id']
        n_item['title'] = item['title']
        n_item['price'] = float(item['price'])

        specs = properties[item['id']]['description_f']
        n_item = {**n_item, **normalize_product(inventory.category_name, specs)}

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

    print(f"{log_tag} Dumping {len(normalized_inventory)} products to {inventory.normalized_file_path}")
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
