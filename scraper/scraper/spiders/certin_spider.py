import scrapy
from scraper.items import RawArticleItem

class CertInSpider(scrapy.Spider):
    name = "certin"
    allowed_domains = ["cert-in.org.in"]
    start_urls = ["https://www.cert-in.org.in/s2cMainServlet?pageid=PUBVLNOTES01"]

    def parse(self, response):
        for link in response.css("a[href*='PUBVLNOTES02']::attr(href)").getall():
            yield response.follow(link, self.parse_advisory)

    def parse_advisory(self, response):
        title = response.css("h1::text").get("").strip()
        if not title:
            title = response.css("b::text").get("CERT-In Advisory").strip()
            
        content = " ".join(response.css("table *::text").getall()).strip()
        
        yield RawArticleItem(
            source_name="CERT-In",
            source_url=response.url,
            title=title,
            content=content,
            published_at=None,
        )
