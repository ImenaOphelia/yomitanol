BOT_NAME = "rae_dictionary"

SPIDER_MODULES = ["rae_dictionary.spiders"]
NEWSPIDER_MODULE = "rae_dictionary.spiders"

# Custom settings
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 16
DOWNLOAD_DELAY = 1
COOKIES_ENABLED = True

CONCURRENT_REQUESTS_PER_DOMAIN = 16
CONCURRENT_REQUESTS_PER_IP = 16

# Updated retry settings
RETRY_ENABLED = True
RETRY_TIMES = 5  # Increased from 3 to 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 520, 408, 429]  # Added 520
RETRY_DELAY = 5  # Added explicit retry delay

# Allow 520 status code
HTTPERROR_ALLOWED_CODES = [520]

DUPEFILTER_CLASS = "scrapy.dupefilters.BaseDupeFilter"

DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
    "DNT": "1",
    "Sec-GPC": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Priority": "u=0, i",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

DOWNLOADER_MIDDLEWARES = {
    "rae_dictionary.middlewares.RaeDictionaryDownloaderMiddleware": 543,
    # Add retry middleware explicitly
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
}

ITEM_PIPELINES = {
    "rae_dictionary.pipelines.RaeDictionaryPipeline": 300,
    "rae_dictionary.pipelines.TagsPipeline": 400,
}

# Additional settings for better error handling
DOWNLOAD_TIMEOUT = 30  # Timeout in seconds
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 5

# Handle network errors
DOWNLOAD_FAIL_ON_DATALOSS = False
