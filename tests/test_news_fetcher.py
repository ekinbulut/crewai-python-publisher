import sys
import os
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
    
    # Initialize the tool
    news_tool = RSSNewsFetcherTool()
    
    try:
        # Test the tool
        logger.info("Executing news fetcher")
        result = news_tool._run("")
        
        if "Error fetching news" in result:
            logger.error("Test failed - received error response")
            return False
            
        # Check if we got actual news items
        news_items = result.split("\n---\n")
        logger.info(f"Retrieved {len(news_items)} news items")
        
        # Test feed fetching directly to verify date filtering
        test_feed = feedparser.parse('https://techcrunch.com/feed/')
        if test_feed.entries:
            latest_entry = test_feed.entries[0]
            if 'published' in latest_entry:
                logger.info(f"Latest feed entry date: {latest_entry.published}")
                if not is_recent_date(latest_entry.published):
                    logger.warning("Test feed contains old entries")
        
        # Validate each news item has required components and is recent
        valid_items = 0
        for item in news_items:
            if not all(x in item for x in ["Title:", "Link:", "Summary:"]):
                logger.error("Test failed - missing required fields in news item")
                return False
            
            # Extract date from item if available
            if "Date:" in item:
                date_line = [line for line in item.split("\n") if "Date:" in line][0]
                date_str = date_line.split("Date:")[1].strip()
                if not is_recent_date(date_str):
                    logger.warning(f"Old news item found: {date_str}")
                else:
                    valid_items += 1
        
        if valid_items == 0:
            logger.warning("No recent news items found")
        else:
            logger.info(f"Found {valid_items} recent news items")
        
        logger.info("Test passed successfully")
        logger.info("Sample of fetched news:")
        # Print first news item as sample
        if news_items:
            logger.info(f"\n{news_items[0]}")
            
        return True
        
    except Exception:
        logger.exception("Test failed with exception")
        return False

if __name__ == "__main__":
    success = test_news_fetcher()
    print(f"\nTest {'passed' if success else 'failed'}")
