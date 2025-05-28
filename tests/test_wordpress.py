from tools.wordpress_poster_tool import WordPressPosterTool
from logger import setup_logger
import sys
import os
import json

logger = setup_logger()

def test_wordpress_post():
    logger.info("Testing WordPress poster directly")
    
    # Log environment variables (without sensitive data)
    wp_url = os.getenv('WORDPRESS_URL')
    wp_user = os.getenv('WORDPRESS_USER')
    logger.info(f"WordPress URL configured: {'Yes' if wp_url else 'No'}")
    logger.info(f"WordPress User configured: {'Yes' if wp_user else 'No'}")
    
    try:
        wordpress_tool = WordPressPosterTool()
        
        # Test post data
        post_data = {
            "title": "Test Blog Post",
            "content": "This is a test blog post content.\n\nThis is a multi-paragraph test.",
            "tags": ["test", "technology"],
            "categories": [5]
        }
        
        logger.info(f"Sending post data:\n{json.dumps(post_data, indent=2)}")
        logger.info("Attempting to post to WordPress...")
        
        result = wordpress_tool._run(post_data)
        logger.info(f"Raw response:\n{json.dumps(result, indent=2)}")
        
        if isinstance(result, dict) and 'id' in result:
            logger.info(f"Post created successfully!")
            logger.info(f"Post ID: {result['id']}")
            logger.info(f"Post URL: {result.get('link', 'No link available')}")
            logger.info(f"Post Status: {result.get('status', 'unknown')}")
        else:
            logger.error(f"Unexpected response format: {type(result)}")
            logger.error(f"Response content: {result}")
            
    except Exception as e:
        logger.error(f"Error testing WordPress poster: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        test_wordpress_post()
    except Exception as e:
        logger.error("Test failed", exc_info=True)
        sys.exit(1)
