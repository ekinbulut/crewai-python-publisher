from crewai.tools import BaseTool
from pydantic import Field
import feedparser
from logger import setup_logger
import time
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

logger = setup_logger()

class RSSNewsFetcherTool(BaseTool):
    name: str = Field(default="rss_news_fetcher")
    description: str = Field(default="Fetches the latest IT news headlines and summaries from popular RSS feeds")

    def _is_recent(self, entry: Dict[str, Any]) -> bool:
        """Check if an entry is from the last 24 hours"""
        try:
            # Try to get the published time
            published = entry.get('published_parsed') or entry.get('updated_parsed')
            if not published:
                return True  # If we can't determine the date, include it
            
            entry_date = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc)
            cutoff_date = datetime.now(timezone.utc) - timedelta(hours=24)
            
            return entry_date >= cutoff_date
        except Exception as e:
            logger.warning(f"Error checking entry date: {str(e)}")
            return True  # Include entries where we can't determine the date

    def _get_entry_summary(self, entry: Dict[str, Any]) -> str:
        """Extract and clean up entry summary"""
        try:
            # Try different fields that might contain the content
            summary = None
            
            # Try the summary field first
            if 'summary' in entry:
                summary = entry['summary']
            # Then try description
            elif 'description' in entry:
                summary = entry['description']
            # Finally try content
            elif 'content' in entry and entry['content']:
                content_list = entry['content']
                if isinstance(content_list, list) and content_list:
                    summary = content_list[0].get('value', '')
            
            if not summary:
                return "No summary available"
            
            # Clean up the summary
            if isinstance(summary, str):
                # Remove newlines and extra spaces
                summary = ' '.join(summary.split())
                # Truncate if too long
                if len(summary) > 500:
                    summary = summary[:497] + "..."
                return summary
            else:
                return "Summary format not supported"
                
        except Exception as e:
            logger.warning(f"Error extracting summary: {str(e)}")
            return "Error extracting summary"

    def _run(self, argument: str) -> str:
        logger.info("Starting RSS News Fetcher Tool execution")
        start_time = time.time()
        
        try:
            feeds = [
                'https://techcrunch.com/feed/',
                'https://www.theverge.com/rss/index.xml',
                'https://www.wired.com/feed/rss'
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
                    
                    # Filter for recent entries and get the top 3
                    recent_entries = [e for e in feed.entries if self._is_recent(e)][:3]
                    
                    logger.info(f"Successfully fetched {len(recent_entries)} recent entries from {url}")
                    for entry in recent_entries:
                        title = entry.get("title", "No title")
                        link = entry.get("link", "No link")
                        summary = self._get_entry_summary(entry)
                        
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
