import os
import pytest
import responses
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from tools.wordpress_poster_tool import WordPressPosterTool
from logger import setup_logger

logger = setup_logger()
load_dotenv()

@pytest.fixture
def wordpress_tool():
    return WordPressPosterTool()

@responses.activate
def test_get_or_create_tag(wordpress_tool):
    """Test tag fetching and creation functionality"""
    base_url = "https://example.com"
    tags_url = f"{base_url}/wp-json/wp/v2/tags"

    # Mock environment variables
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        # Mock the GET request to search for existing tag
        rsps.add(
            responses.GET,
            f"{tags_url}?search=technology",
            json=[{"id": 1, "name": "technology"}],
            status=200
        )

        # Mock the GET request for a non-existent tag
        rsps.add(
            responses.GET,
            f"{tags_url}?search=newtag",
            json=[],
            status=200
        )

        # Mock the POST request to create a new tag
        rsps.add(
            responses.POST,
            tags_url,
            json={"id": 2, "name": "newtag"},
            status=201
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("WORDPRESS_URL", f"{base_url}/wp-json/wp/v2/posts")
            mp.setenv("WORDPRESS_USER", "testuser")
            mp.setenv("WORDPRESS_PASS", "testpass")

            # Create auth object for testing
            auth = HTTPBasicAuth("testuser", "testpass")

            # Test finding existing tag
            tag_id = wordpress_tool._get_or_create_tag("technology", auth)
            assert tag_id == 1

            # Test creating new tag
            tag_id = wordpress_tool._get_or_create_tag("newtag", auth)
            assert tag_id == 2

@responses.activate
def test_post_with_tags(wordpress_tool):
    """Test posting content with tags"""
    base_url = "https://example.com"
    api_url = f"{base_url}/wp-json/wp/v2/posts"
    tags_url = f"{base_url}/wp-json/wp/v2/tags"

    # Test post data
    post_data = {
        "title": "Test Post with Tags",
        "content": "This is test content",
        "tags": ["technology", "ai"],
        "categories": [5]
    }

    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        # Mock tag search responses
        rsps.add(
            responses.GET,
            f"{tags_url}?search=technology",
            json=[{"id": 1, "name": "technology"}],
            status=200
        )
        rsps.add(
            responses.GET,
            f"{tags_url}?search=ai",
            json=[{"id": 2, "name": "ai"}],
            status=200
        )

        # Mock successful post creation
        rsps.add(
            responses.POST,
            api_url,
            json={
                "id": 123,
                "link": f"{base_url}/test-post",
                "title": {"rendered": post_data["title"]},
                "content": {"rendered": post_data["content"]},
                "tags": [1, 2]
            },
            status=201,
            match=[responses.json_params_matcher({
                "title": {"raw": post_data["title"]},
                "content": {"raw": post_data["content"]},
                "status": "draft",
                "categories": post_data["categories"],
                "tags": [1, 2]
            })]
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setenv("WORDPRESS_URL", api_url)
            mp.setenv("WORDPRESS_USER", "testuser")
            mp.setenv("WORDPRESS_PASS", "testpass")

            # Post content with tags
            result = wordpress_tool._run(post_data)

            # Verify response
            assert result["id"] == 123
            assert result["tags"] == [1, 2]
