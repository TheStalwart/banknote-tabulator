# veikals.banknote.lv scraper

[The shop](https://veikals.banknote.lv/c/datortehnika/portativie-datori) 
often has good deals in stock 
but doesn't allow filtering laptops by RAM,
among other UI/UX mortal sins.

I'm hosting an instance 
at [banknote.retromultiplayer.com](https://banknote.retromultiplayer.com/)


## Development environment

### Docker-based
To refresh inventory, run download-products.py:
`docker-compose up downloader`

To run a local web server at http://127.0.0.1:3000:
`docker-compose up web`

### venv-based
To create venv:
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

To refresh inventory:
`.venv/bin/python3 download-products.py`

### DevContainer-based
`.devcontainer/devcontainer.json` contains a `postCreateCommand` that will attempt to download and unpack database archive from production instance to avoid doing a full scrape. 

To run HTTPd in DevContainer:
`python -m http.server 8080`

The easiest way to create a development environment is to use GitHub Codespaces.
