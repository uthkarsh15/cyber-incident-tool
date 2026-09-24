FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command to run a spider, though usually triggered by cron
CMD ["scrapy", "crawl", "news"]
