# veikals.banknote.lv scraper

[The shop](https://veikals.banknote.lv/c/datortehnika/portativie-datori)
often has good deals in stock
but doesn't allow filtering laptops by RAM,
among other UI/UX mortal sins.

I'm hosting an instance
at [banknote.retromultiplayer.com](https://banknote.retromultiplayer.com/)

## Sentry.io SDK integration

To enable [Sentry.io SDK](https://docs.sentry.io/platforms/python/),
create `sentry.dsn` file with Client Key (DSN) in the root of the project.

## Better Stack heartbeat monitor

To enable [Better Stack heartbeat monitor](https://betterstack.com/docs/uptime/cron-and-heartbeat-monitor/),
create `heartbeat.url` file with heartbeat URL in the root of the project.

## Development environment

### Docker-based

To refresh inventory, run download-products.py:
`docker compose up downloader`

To run a local web server at <http://127.0.0.1:3000>:
`docker compose up web`

### venv-based

To create venv:
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

To refresh inventory:
`.venv/bin/python3 download-products.py`

Optionally set the delay in seconds between HTTP requests:
`.venv/bin/python3 download-products.py --delay=20`

### DevContainer-based

`.devcontainer/devcontainer.json` contains a `postCreateCommand` that will attempt to download and unpack database archive from production instance to avoid doing a full scrape.

To run HTTPd in DevContainer:
`python -m http.server 8080`

The easiest way to create a development environment is to use GitHub Codespaces.

## Configuring categories

The script supports multiple categories. To add new ones:

1. In `download-products.py`:
   1. Edit the `known_categories` list somewhere at the top.
   2. Edit the `normalize_product` function right below the list.
   3. Edit the `categories_to_fetch` variable's default value.
2. In `banknote-tabulator.js`, edit the `categories` array at the top.

Make sure the category and field names match.

## Storage

The products are saved in plain JSON files, sorted by categories:

```plaintext
inventory/
    <CATEGORY NAME>/
        archives/
            <DATE AND TIME>.zip
            latest.zip
        products/
            <ID>/
                <DATE AND TIME>.json
                last_seen
    <OTHER CATEGORY NAME>/
        ...
```
