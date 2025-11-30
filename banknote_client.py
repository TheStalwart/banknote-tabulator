import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

class BanknoteClient:
    def __init__(self):
        # use session to preserve cookies, add some realistic browser headers
        self.session = requests.Session()

        # Set up a Retry policy to avoid crashing on monthly DNS resolution failures
        # https://stackoverflow.com/questions/23013220/max-retries-exceeded-with-url-in-requests
        request_retry_config = Retry(total=5, backoff_factor=15)
        http_adapter = HTTPAdapter(max_retries=request_retry_config)
        self.session.mount('http://', http_adapter)
        self.session.mount('https://', http_adapter)

        self.session.headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-GB,en;q=0.7',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
        })
        # initialize cookies
        self.get('https://veikals.banknote.lv/lv/')

    # get page and update cookies
    def get(self, url, **kwargs):
        response = self.session.get(url, **kwargs)
        return response
