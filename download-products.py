import requests
import json
import os
import time
from datetime import datetime
import math
from bs4 import BeautifulSoup
import re
import pathlib


# Keep cache of entire inventory in RAM
products = []


# Define inventory file storage paths
root = pathlib.Path(__file__).parent.resolve()
folder = os.path.join(root, "inventory")
index_file_name = "index.json"
index_file_path = os.path.join(folder, index_file_name)


def download_index():
    print("Downloading first page...")
    # https://requests.readthedocs.io/en/latest/user/quickstart/#passing-parameters-in-urls
    r = requests.get('https://veikals.banknote.lv/lv/filter-products', params={'categories': 8, 'page': 1})
    first_page = r.json()
    products.extend(first_page['data'])

    last_page_number = first_page['last_page']
    print(f"Total amount of pages: {last_page_number}")

    for page_number in range(2, last_page_number+1):
        print(f"Downloading page #{page_number}")
        r = requests.get('https://veikals.banknote.lv/lv/filter-products', params={'categories': 8, 'page': page_number})
        extra_page = r.json()
        products.extend(extra_page['data'])

    # https://www.geeksforgeeks.org/reading-and-writing-json-to-a-file-in-python/
    print(f"Dumping {len(products)} products to {index_file_path}")
    with open(index_file_path, "w") as index_file:
        json.dump(products, index_file, indent=2)
        return os.path.getmtime(index_file_path)


# Update inventory index if necessary
if not os.path.isfile(index_file_path):
    index_file_modification_timestamp = download_index()
else:
    try:
        # Check index file age
        INDEX_FILE_MAX_AGE_MINUTES = 55
        index_file_modification_timestamp = os.path.getmtime(index_file_path)
        current_timestamp = time.time()
        index_file_age_seconds = current_timestamp - index_file_modification_timestamp
        index_file_age_minutes = math.floor(index_file_age_seconds / 60)
        print(f"Index file is {index_file_age_minutes} minutes old")

        if index_file_age_minutes < INDEX_FILE_MAX_AGE_MINUTES:
            print(f"Loading inventory from {index_file_name}")
            index_file = open(index_file_path)
            products = json.load(index_file)
            print(f"Loaded {len(products)} products from {index_file_path}")
        else:
            index_file_modification_timestamp = download_index()
    except:
        print(f"Failed to parse index file, redownloading")
        index_file_modification_timestamp = download_index()


# Load additional properties absent in index
properties = {}
for item in products:
    item_file_path = os.path.join(folder, f"{item['id']}.json")
    if (os.path.isfile(item_file_path)) and (os.path.getsize(item_file_path) > 0):
        item_file = open(item_file_path)
        product_properties = json.load(item_file)
        if item['price'] == product_properties['price']:
            # print(f"{item['id']} details already downloaded")
            product_properties['item_file_path'] = item_file_path
            properties[item['id']] = product_properties
            continue

    print(f"Downloading details of {item['id']}: {item['title']}")
    r = requests.get(item['url'])
    html_contents = r.text
    soup = BeautifulSoup(html_contents, 'html.parser')  
    leasing_item = soup.find('product-item-leasing')
    product_data = leasing_item[':product']
    product_properties = json.loads(product_data)
    with open(item_file_path, "w", encoding='utf-8') as item_file:
        json.dump(product_properties, item_file, indent=2)
    product_properties['item_file_path'] = item_file_path
    properties[item['id']] = product_properties


# Normalize data for use in frontend
normalized_file_name = "normalized.json"
normalized_file_path = os.path.join(folder, normalized_file_name)
normalized_inventory = []
for item in products:
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
        if re.search('(atmi|disk|hdd|ssd)', entry['title'], re.IGNORECASE) and not re.search('(oper)', entry['title'], re.IGNORECASE):
            n_item['storage'] = entry['value'].strip()
        if re.search('(gpu|video)', entry['title'], re.IGNORECASE):
            n_item['gpu'] = entry['value'].strip(' -"')

    address_components = item['branche']['address'].split('<br>')
    n_item['city'] = address_components[0].strip(' ,')
    n_item['local_address'] = address_components[1].strip(' ,')

    n_item['url'] = item['url']

    n_item['images'] = []
    for image_data in properties[item['id']]['erp_images']:
        n_item['images'].append(f"https://veikals.banknote.lv/storage/{image_data['path']}")
        
    n_item['timestamp'] = datetime.fromtimestamp(os.path.getmtime(properties[item['id']]['item_file_path'])).isoformat()

    normalized_inventory.append(n_item)

print(f"Dumping {len(normalized_inventory)} products to {normalized_file_path}")
inventory_dictionary = {
    'index_file_modification_timestamp': index_file_modification_timestamp,
    'inventory': normalized_inventory,
}
with open(normalized_file_path, "w", encoding='utf-8') as normalized_file:
    json.dump(inventory_dictionary, normalized_file, indent=2)
