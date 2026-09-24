import scrapy
from scraper.items import RawArticleItem

class NewsSpider(scrapy.Spider):
    name = "news"
    allowed_domains = ["thehackernews.com"]
    start_urls = ["https://thehackernews.com/"]

    def parse(self, response):
        for link in response.css("a.story-link::attr(href)").getall():
            yield response.follow(link, self.parse_article)

    def parse_article(self, response):
        title = response.css("h1.story-title::text").get("").strip()
        content = " ".join(response.css("div.articlebody *::text").getall()).strip()
        published_at = response.css("span.author::text").get("").replace('\ue80a', '').strip()
        
        yield RawArticleItem(
            source_name="The Hacker News",
            source_url=response.url,
            title=title,
            content=content,
            published_at=published_at,
        )
