import os
import pytest
import responses
from dotenv import load_dotenv
from tools.wordpress_poster_tool import WordPressPosterTool
from logger import setup_logger

logger = setup_logger()
load_dotenv()  # Load environment variables at module level

@pytest.fixture
def wordpress_tool():
    return WordPressPosterTool(
        name="wordpress_poster",
        description="Posts content to a WordPress blog using the REST API"
    )

def test_build_api_url():
    tool = WordPressPosterTool(
        name="wordpress_poster",
        description="Posts content to a WordPress blog using the REST API"
    )
    # Test with clean URL
    assert tool._build_api_url('https://example.com') == 'https://example.com/wp-json/wp/v2/posts'
    # Test with trailing slash
    assert tool._build_api_url('https://example.com/') == 'https://example.com/wp-json/wp/v2/posts'
    # Test with wp-json already in URL
    assert tool._build_api_url('https://example.com/wp-json') == 'https://example.com/wp-json/wp/v2/posts'
    # Test with no scheme
    assert tool._build_api_url('example.com') == 'https://example.com/wp-json/wp/v2/posts'

@responses.activate
def test_successful_post(wordpress_tool):
    wordpress_url = os.getenv('WORDPRESS_URL', 'https://example.com')
    api_url = wordpress_tool._build_api_url(wordpress_url)
    
    # Mock successful response
    responses.add(
        responses.POST,
        api_url,
        json={'id': 123, 'link': f'{wordpress_url}/test-post'},
        status=200
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("WORDPRESS_URL", wordpress_url)
        mp.setenv("WORDPRESS_USER", "user")
        mp.setenv("WORDPRESS_PASS", "pass")

        result = wordpress_tool._run(
            "Test Blog Post Title",
            "This is a test blog post content.",
            [],
            []
        )

    assert result["id"] == 123
    assert result["link"].endswith("/test-post")

@responses.activate
def test_authentication_error(wordpress_tool):
    wordpress_url = os.getenv('WORDPRESS_URL', 'https://example.com')
    api_url = wordpress_tool._build_api_url(wordpress_url)
    
    # Mock authentication error
    responses.add(
        responses.POST,
        api_url,
        json={'code': 'rest_not_logged_in', 'message': 'Invalid credentials'},
        status=401
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("WORDPRESS_URL", wordpress_url)
        mp.setenv("WORDPRESS_USER", "user")
        mp.setenv("WORDPRESS_PASS", "bad")
        with pytest.raises(ValueError) as exc_info:
            wordpress_tool._run(
                "Test Blog Post Title",
                "This is a test blog post content.",
                [],
                []
            )
    assert 'Authentication failed' in str(exc_info.value)

@responses.activate
def test_invalid_endpoint(wordpress_tool):
    wordpress_url = os.getenv('WORDPRESS_URL', 'https://example.com')
    api_url = wordpress_tool._build_api_url(wordpress_url)
    
    # Mock 404 response
    responses.add(
        responses.POST,
        api_url,
        json={'code': 'rest_no_route'},
        status=404
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("WORDPRESS_URL", wordpress_url)
        mp.setenv("WORDPRESS_USER", "user")
        mp.setenv("WORDPRESS_PASS", "pass")

        with pytest.raises(ValueError) as exc_info:
            wordpress_tool._run(
                "Test Blog Post Title",
                "This is a test blog post content.",
                [],
                []
            )
    assert 'API endpoint not found' in str(exc_info.value)

def test_empty_post(wordpress_tool):
    with pytest.raises(ValueError) as exc_info:
        wordpress_tool._run("Test", "", [], [])
    assert 'Content cannot be empty' in str(exc_info.value)

def test_missing_title(wordpress_tool):
    with pytest.raises(ValueError) as exc_info:
        wordpress_tool._run("", "content", [], [])
    assert 'Title cannot be empty' in str(exc_info.value)

def test_missing_env_vars():
    # Save current environment variables
    original_url = os.environ.get('WORDPRESS_URL')
    original_user = os.environ.get('WORDPRESS_USER')
    original_pass = os.environ.get('WORDPRESS_PASS')
    
    # Temporarily remove environment variables
    if 'WORDPRESS_URL' in os.environ:
        del os.environ['WORDPRESS_URL']
    if 'WORDPRESS_USER' in os.environ:
        del os.environ['WORDPRESS_USER']
    if 'WORDPRESS_PASS' in os.environ:
        del os.environ['WORDPRESS_PASS']
    
    try:
        tool = WordPressPosterTool(
            name="wordpress_poster",
            description="Posts content to a WordPress blog using the REST API"
        )
        with pytest.raises(ValueError) as exc_info:
            tool._run("Test", "Content", [], [])
        assert 'WORDPRESS_URL not set' in str(exc_info.value)
    finally:
        # Restore environment variables
        if original_url:
            os.environ['WORDPRESS_URL'] = original_url
        if original_user:
            os.environ['WORDPRESS_USER'] = original_user
        if original_pass:
            os.environ['WORDPRESS_PASS'] = original_pass
