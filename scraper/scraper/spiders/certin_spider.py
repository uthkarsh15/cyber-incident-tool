import re
import scrapy
from scraper.items import RawArticleItem


class CertInSpider(scrapy.Spider):
    name = "certin"
    allowed_domains = ["cert-in.org.in"]
    start_urls = ["https://www.cert-in.org.in/s2cMainServlet?pageid=VLNLIST"]

    def parse(self, response):
        detail_pattern = re.compile(r"pageid=[A-Z0-9]+", re.IGNORECASE)
        all_links = response.css("a::attr(href)").getall()
        for link in all_links:
            if not link or link.startswith("javascript:") or link.startswith("#"):
                continue
            if detail_pattern.search(link) and "VLNLIST" not in link and "PUBADVLIST" not in link:
                yield response.follow(link, self.parse_advisory)

        for onclick in response.css("tr[onclick], td[onclick], a[onclick]").re(
            r"location\.href=['\"]([^'\"]+)['\"]|callSearch\(['\"]([^'\"]+)['\"]\)"
        ):
            if onclick:
                if onclick.startswith("/"):
                    yield response.follow(onclick, self.parse_advisory)
                elif not onclick.startswith(("http", "#", "javascript")):
                    from scrapy.utils.httpobj import urlparse_cached
                    yield response.follow(
                        f"{urlparse_cached(response).scheme}://{urlparse_cached(response).netloc}/s2cMainServlet?pageid={onclick}",
                        self.parse_advisory,
                    )

    def parse_advisory(self, response):
        title = " ".join(response.css("h1 ::text, h2 ::text").getall()).strip()
        if not title:
            title = response.css("meta[property='og:title']::attr(content)").get("").strip()
        if not title:
            title = "CERT-In Advisory / Vulnerability Note"

        content_parts = []
        for sel in ["table *::text", "article *::text", "div[class*='content'] *::text", "body *::text"]:
            text = " ".join(response.css(sel).getall()).strip()
            if len(text) > len(content_parts):
                content_parts = [text]
        content = content_parts[0] if content_parts else ""

        published_at = ""
        date_pattern = re.compile(
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}"
            r"|\d{4}-\d{2}-\d{2}"
            r"|\d{1,2}/\d{1,2}/\d{4}"
        )
        for candidate in [
            " ".join(response.css("span ::text").getall()),
            " ".join(response.css("td ::text").getall()),
            response.text[:5000],
        ]:
            match = date_pattern.search(candidate or "")
            if match:
                published_at = match.group(0)
                break

        yield RawArticleItem(
            source_name="CERT-In",
            source_url=response.url,
            title=title,
            content=content,
            published_at=published_at,
        )
