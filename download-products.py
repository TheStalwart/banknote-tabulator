import requests
import json
import os

products = []

# https://requests.readthedocs.io/en/latest/user/quickstart/#passing-parameters-in-urls
print("Downloading first page...")
r = requests.get('https://veikals.banknote.lv/lv/filter-products', params={'categories': 8, 'page': 1})
firstPage = r.json()
products.extend(firstPage['data'])

lastPageNumber = firstPage['last_page']
print(f"Total amount of pages: {lastPageNumber}")

for pageNumber in range(2, lastPageNumber+1):
    print(f"Downloading page #{pageNumber}")
    r = requests.get('https://veikals.banknote.lv/lv/filter-products', params={'categories': 8, 'page': pageNumber})
    extraPage = r.json()
    products.extend(extraPage['data'])

# https://www.geeksforgeeks.org/reading-and-writing-json-to-a-file-in-python/
folder = "inventory"
fileName = "index.json"
filePath = os.path.join(folder, fileName)
print(f"Dumping {len(products)} products to {filePath}")
with open(filePath, "w") as outfile:
    json.dump(products, outfile)
