BOT_NAME = 'rae_dictionary'

SPIDER_MODULES = ['rae_dictionary.spiders']
NEWSPIDER_MODULE = 'rae_dictionary.spiders'

# Custom settings
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS = 16
DOWNLOAD_DELAY = 1
COOKIES_ENABLED = True

CONCURRENT_REQUESTS_PER_DOMAIN = 16
CONCURRENT_REQUESTS_PER_IP = 16

RETRY_ENABLED = True
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

DUPEFILTER_CLASS = "scrapy.dupefilters.BaseDupeFilter"

DEFAULT_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
    # 'Accept-Encoding': 'gzip, deflate, br, zstd',
    'DNT': '1',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    # 'Cookie': 'TS01b02f89=017ccc203ccc6bfcfcc727944ca7c4355a6b4f6d02abb1394f61466b2f978e30dee048f4e68644da8d69a12af7556b3299287fa45f',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Priority': 'u=0, i',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    # Requests doesn't support trailers
    # 'TE': 'trailers',
}

DOWNLOADER_MIDDLEWARES = {
    'rae_dictionary.middlewares.RaeDictionaryDownloaderMiddleware': 543,
}

ITEM_PIPELINES = {
    'rae_dictionary.pipelines.RaeDictionaryPipeline': 300,
    'rae_dictionary.pipelines.TagsPipeline': 400,
}