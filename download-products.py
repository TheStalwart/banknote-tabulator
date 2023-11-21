import requests
import json
import os

products = []

# https://requests.readthedocs.io/en/latest/user/quickstart/#passing-parameters-in-urls
print("Downloading first page...")
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
folder = "inventory"
file_name = "index.json"
file_path = os.path.join(folder, file_name)
print(f"Dumping {len(products)} products to {file_path}")
with open(file_path, "w") as outfile:
    json.dump(products, outfile)
