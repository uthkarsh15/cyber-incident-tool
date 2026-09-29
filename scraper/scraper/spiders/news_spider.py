import re
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
        title = " ".join(response.css("h1.story-title ::text").getall()).strip()
        if not title:
            title = response.css("meta[property='og:title']::attr(content)").get("").strip()

        content = " ".join(response.css("div.articlebody *::text").getall()).strip()

        published_at = None
        date_text_pool = " ".join(
            response.css("span.author ::text, span.p-author ::text, "
                         "span.expert-datetime ::text, time ::text, "
                         ".post-header ::text, header ::text").getall()
        )
        date_pattern = re.compile(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}"
            r"|\d{4}-\d{2}-\d{2}"
        )
        cleaned_pool = (
            date_text_pool.replace("\ue802", " ")
                           .replace("\ue804", " ")
                           .replace("\ue80a", " ")
        )
        match = date_pattern.search(cleaned_pool)
        published_at = match.group(0) if match else ""

        yield RawArticleItem(
            source_name="The Hacker News",
            source_url=response.url,
            title=title,
            content=content,
            published_at=published_at,
        )
