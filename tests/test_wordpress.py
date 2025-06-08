from tools.wordpress_poster_tool import WordPressPosterTool
from logger import setup_logger
import os
import json
import pytest

logger = setup_logger()


@pytest.mark.skip(reason="Requires WordPress server access")
def test_wordpress_post():
    logger.info("Testing WordPress poster directly")
    
    # Log environment variables (without sensitive data)
    wp_url = os.getenv('WORDPRESS_URL')
    wp_user = os.getenv('WORDPRESS_USER')
    logger.info(f"WordPress URL configured: {'Yes' if wp_url else 'No'}")
    logger.info(f"WordPress User configured: {'Yes' if wp_user else 'No'}")
    
    wordpress_tool = WordPressPosterTool()

    post_data = {
        "title": "Test Blog Post",
        "content": "This is a test blog post content.\n\nThis is a multi-paragraph test.",
        "tags": ["test", "technology"],
        "categories": [5]
    }

    logger.info(f"Sending post data:\n{json.dumps(post_data, indent=2)}")
    logger.info("Attempting to post to WordPress...")

    result = wordpress_tool._run(
        post_data["title"],
        post_data["content"],
        post_data["tags"],
        post_data["categories"]
    )
    logger.info(f"Raw response:\n{json.dumps(result, indent=2)}")

    assert isinstance(result, dict) and "id" in result
