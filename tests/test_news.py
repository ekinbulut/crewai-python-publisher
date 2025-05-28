from tools.news_fetcher_tool import RSSNewsFetcherTool
from logger import setup_logger
import sys

logger = setup_logger()
logger.info("Testing news fetcher directly")

try:
    news_tool = RSSNewsFetcherTool()
    result = news_tool._run("")
    
    news_items = result.split("\n---\n")
    logger.info(f"Retrieved {len(news_items)} news items")
    
    print("\nFirst 3 news items:\n")
    for i, item in enumerate(news_items[:3]):
        print(f"\n=== News Item {i+1} ===\n{item}\n")
except Exception as e:
    logger.error(f"Error testing news fetcher: {str(e)}")
    sys.exit(1)
