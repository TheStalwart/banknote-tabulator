# veikals.banknote.lv scraper

[The shop](https://veikals.banknote.lv/c/datortehnika/portativie-datori) 
often has good deals in stock 
but doesn't allow filtering laptops by RAM,
among other UI/UX mortal sins.

I'm hosting an instance 
at [banknote.retromultiplayer.com](https://banknote.retromultiplayer.com/)


## Development environment
To refresh inventory, run download-products.py:
`docker-compose up downloader`

To run a local web server at http://127.0.0.1:3000:
`docker-compose up web`
