import os
from dotenv import load_dotenv
from tools.wordpress_poster_tool import WordPressPosterTool
from logger import setup_logger

logger = setup_logger()

def test_wordpress_posting():
    load_dotenv()
    
    # Test data
    test_post = """Test Blog Post Title
This is a test blog post content.
It includes multiple lines
to test the posting functionality."""
    
    # Initialize the tool
    poster_tool = WordPressPosterTool()
    
    # Attempt to post
    try:
        result = poster_tool._run(test_post)
        logger.info(f"Posting result: {result}")
        return True
    except Exception as e:
        logger.error(f"Error testing WordPress poster: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_wordpress_posting()
    print("Test completed successfully" if success else "Test failed")
