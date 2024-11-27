from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

class RaeDictionaryDownloaderMiddleware:
    def __init__(self):
        self.custom_cookies = {
            'TS01b02f89': '017ccc203ccc6bfcfcc727944ca7c4355a6b4f6d02abb1394f61466b2f978e30dee048f4e68644da8d69a12af7556b3299287fa45f',
        }
        
        self.custom_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'DNT': '1',
    'Sec-GPC': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'cross-site',
    'Priority': 'u=0, i',
    'Pragma': 'no-cache',
    'Cache-Control': 'no-cache',
    'TE': 'trailers',
        }

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def process_request(self, request, spider):
        for cookie_name, cookie_value in self.custom_cookies.items():
            request.cookies[cookie_name] = cookie_value

        for header_name, header_value in self.custom_headers.items():
            request.headers[header_name] = header_value

        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)