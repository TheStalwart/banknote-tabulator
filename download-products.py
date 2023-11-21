import requests
import json
import os
import time
import datetime
import math
from bs4 import BeautifulSoup


# Keep cache of entire inventory in RAM
products = []


# Define inventory file storage paths
folder = "inventory"
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


# Update inventory index if necessary
if not os.path.isfile(index_file_path):
    download_index()
else:
    try:
        # Check index file age
        INDEX_FILE_MAX_AGE_MINUTES = 60
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
            download_index()
    except:
        print(f"Failed to parse index file, redownloading")
        download_index()


# Update inventory details if missing
for item in products:
    item_file_path = os.path.join(folder, f"{item['id']}.json")
    if (os.path.isfile(item_file_path)) and (os.path.getsize(item_file_path) > 0):
        print(f"{item['id']} details already downloaded")
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
