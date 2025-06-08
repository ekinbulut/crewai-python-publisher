import sys
import os
import pytest
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.news_fetcher_tool import RSSNewsFetcherTool
from logger import setup_logger
from datetime import datetime, timezone, timedelta
import feedparser

logger = setup_logger()

def is_recent_date(date_str):
    """Check if a date string represents a date within the last 24 hours"""
    try:
        # Try to parse the date string
        parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
        cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
        return parsed_date >= cutoff_date
    except Exception:
        return False

def test_news_fetcher():
    logger.info("Starting News Fetcher Tool test")

    news_tool = RSSNewsFetcherTool()

    logger.info("Executing news fetcher")
    result = news_tool._run("")

    if "Error fetching news" in result or "No news items" in result:
        pytest.skip("RSS feeds unavailable")

    news_items = result.split("\n---\n")
    logger.info(f"Retrieved {len(news_items)} news items")
    assert news_items, "No news items returned"

    test_feed = feedparser.parse('https://techcrunch.com/feed/')
    if test_feed.entries and 'published' in test_feed.entries[0]:
        latest = test_feed.entries[0].published
        logger.info(f"Latest feed entry date: {latest}")
        assert is_recent_date(latest)

    for item in news_items:
        assert all(x in item for x in ["Title:", "Link:", "Summary:"]), "Missing required fields"


