import unittest
from unittest.mock import patch, MagicMock
from tools.wordpress_poster_tool import WordPressPosterTool
import requests

class TestWordPressPosterTool(unittest.TestCase):
    def setUp(self):
        self.tool = WordPressPosterTool()
        self.test_post = """Test Blog Title
This is the content of the test blog post.
It includes multiple lines of text
for testing purposes."""
        
        # Mock successful response
        self.mock_response = MagicMock()
        self.mock_response.status_code = 201
        self.mock_response.json.return_value = {
            "id": 123,
            "link": "https://example.com/test-post",
            "status": "publish"
        }

    @patch('tools.wordpress_poster_tool.requests.post')
    def test_successful_post(self, mock_post):
        mock_post.return_value = self.mock_response
        
        with patch.dict('os.environ', {
            'WORDPRESS_URL': 'https://example.com/wp-json/wp/v2/posts',
            'WORDPRESS_USER': 'testuser',
            'WORDPRESS_PASS': 'testpass'
        }):
            result = self.tool._run(self.test_post)
        
        self.assertIn("Successfully posted article", result)
        self.assertIn("123", result)
        self.assertIn("https://example.com/test-post", result)

    @patch('tools.wordpress_poster_tool.requests.post')
    def test_failed_authentication(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"message": "Invalid credentials"}
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {
            'WORDPRESS_URL': 'https://example.com/wp-json/wp/v2/posts',
            'WORDPRESS_USER': 'testuser',
            'WORDPRESS_PASS': 'wrongpass'
        }):
            with self.assertRaises(RuntimeError) as context:
                self.tool._run(self.test_post)
            
            self.assertIn("Error posting to WordPress", str(context.exception))

if __name__ == '__main__':
    unittest.main()
