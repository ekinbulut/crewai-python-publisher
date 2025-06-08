import unittest
from unittest.mock import patch, MagicMock
import requests
from tools.wordpress_poster_tool import WordPressPosterTool

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
            result = self.tool._run(
                "Test Blog Title",
                "This is the content of the test blog post.\nIt includes multiple lines of text\nfor testing purposes.",
                [],
                []
            )

        self.assertEqual(result["id"], 123)
        self.assertEqual(result["link"], "https://example.com/test-post")

    @patch('tools.wordpress_poster_tool.requests.post')
    def test_failed_authentication(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.ok = False
        mock_response.json.return_value = {"message": "Invalid credentials"}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        
        with patch.dict('os.environ', {
            'WORDPRESS_URL': 'https://example.com/wp-json/wp/v2/posts',
            'WORDPRESS_USER': 'testuser',
            'WORDPRESS_PASS': 'wrongpass'
        }):
            with self.assertRaises(ValueError) as context:
                self.tool._run(
                    "Test Blog Title",
                    "This is the content of the test blog post.\nIt includes multiple lines of text\nfor testing purposes.",
                    [],
                    []
                )

            self.assertIn("Authentication failed", str(context.exception))
