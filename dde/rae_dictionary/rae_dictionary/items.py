import scrapy


class DictionaryItem(scrapy.Item):
    url = scrapy.Field()
    word = scrapy.Field()
    type = scrapy.Field()
    data = scrapy.Field()
    timestamp = scrapy.Field()
