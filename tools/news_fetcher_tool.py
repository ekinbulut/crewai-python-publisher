from crewai.tools import BaseTool
from pydantic import Field
import feedparser
from logger import setup_logger
import time

logger = setup_logger()

class RSSNewsFetcherTool(BaseTool):
    name: str = Field(default="rss_news_fetcher")
    description: str = Field(default="Fetches the latest IT news headlines and summaries from popular RSS feeds")

    def _run(self, argument: str) -> str:
        logger.info("Starting RSS News Fetcher Tool execution")
        start_time = time.time()
        
        try:
            feeds = [
                'https://techcrunch.com/feed/',
                'https://www.theverge.com/rss/index.xml',
                'https://www.wired.com/feed/rss',
                'https://feeds.arstechnica.com/arstechnica/index'
            ]
            logger.info(f"Configured to fetch from {len(feeds)} RSS feeds")
            
            collected_news = []
            successful_feeds = 0
            
            for url in feeds:
                try:
                    logger.info(f"Attempting to fetch feed: {url}")
                    feed = feedparser.parse(url)
                    
                    if feed.bozo:  # feedparser sets this flag for malformed feeds
                        logger.warning(f"Feed may be malformed: {url}, Error: {feed.bozo_exception}")
                        continue
                    
                    if not feed.entries:
                        logger.warning(f"No entries found in feed: {url}")
                        continue
                        
                    logger.info(f"Successfully fetched {len(feed.entries[:3])} entries from {url}")
                    for entry in feed.entries[:3]:
                        title = entry.get("title", "No title")
                        link = entry.get("link", "No link")
                        summary = entry.get("summary", "No summary")
                        collected_news.append(f"Title: {title}\nLink: {link}\nSummary: {summary}\n")
                    successful_feeds += 1
                    
                except Exception as feed_error:
                    logger.error(f"Error processing feed {url}: {str(feed_error)}")
                    continue

            execution_time = time.time() - start_time
            logger.info(f"News fetching completed. Processed {successful_feeds}/{len(feeds)} feeds successfully in {execution_time:.2f} seconds")
            
            if not collected_news:
                logger.warning("No news items were collected from any feed")
                return "No news items could be fetched at this time."
                
            return "\n---\n".join(collected_news)
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"Critical error in news fetcher after {execution_time:.2f} seconds")
            return f"Error fetching news: {str(e)}"
