from tools.news_fetcher_tool import RSSNewsFetcherTool
from logger import setup_logger

logger = setup_logger()

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
        
        # Validate each news item has required components
        for item in news_items:
            if not all(x in item for x in ["Title:", "Link:", "Summary:"]):
                logger.error("Test failed - missing required fields in news item")
                return False
        
        logger.info("Test passed successfully")
        logger.info("Sample of fetched news:")
        # Print first news item as sample
        if news_items:
            logger.info(f"\n{news_items[0]}")
            
        return True
        
    except Exception as e:
        logger.exception("Test failed with exception")
        return False

if __name__ == "__main__":
    success = test_news_fetcher()
    print(f"\nTest {'passed' if success else 'failed'}")
