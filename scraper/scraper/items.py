import scrapy

class RawArticleItem(scrapy.Item):
    source_name = scrapy.Field()
    source_url = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    published_at = scrapy.Field()
    extra = scrapy.Field()
