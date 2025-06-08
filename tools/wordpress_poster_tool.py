from crewai.tools import BaseTool
from pydantic import Field, BaseModel
import requests
import os
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from logger import setup_logger
from typing import Dict, Any, List, Tuple, Optional
import time

logger = setup_logger()

class WordPressPostData(BaseModel):
    title: str = Field(description="The title of the blog post")
    content: str = Field(description="The full content of the blog post")
    tags: List[str] = Field(description="List of tags for the post")
    categories: List[int] = Field(description="List of category IDs for the post")

class WordPressPosterTool(BaseTool):
    name: str = Field(default="wordpress_poster")
    description: str = Field(default="Posts content to a WordPress blog using the REST API")
    args_schema: type[BaseModel] = WordPressPostData
    _last_request_time: float = 0
    _min_request_interval: float = 2.0  # Minimum seconds between requests
    _max_retries: int = 3

    def _wait_for_rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            logger.debug(f"Rate limiting: waiting {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _make_request_with_retry(self, url: str, auth: HTTPBasicAuth, headers: dict, payload: dict) -> requests.Response:
        """Make HTTP request with retry logic"""
        last_exception = None
        
        for attempt in range(self._max_retries):
            try:
                self._wait_for_rate_limit()
                response = requests.post(
                    url,
                    auth=auth,
                    headers=headers,
                    json=payload,
                    verify=True,
                    timeout=30
                )
                return response
            except (requests.ConnectionError, requests.Timeout) as e:
                last_exception = e
                if attempt < self._max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff
                    logger.warning(f"Request failed, retrying in {wait_time} seconds... ({str(e)})")
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(f"Failed after {self._max_retries} retries: {str(e)}")
        
        raise RuntimeError(f"Failed to make request: {str(last_exception)}")

    def _get_credentials(self) -> Tuple[str, str, str]:
        """Get and validate WordPress credentials"""
        load_dotenv()
        
        url = os.getenv("WORDPRESS_URL")
        user = os.getenv("WORDPRESS_USER")
        password = os.getenv("WORDPRESS_PASS")
        
        logger.debug("Checking WordPress credentials...")
        
        if not url:
            raise ValueError("WORDPRESS_URL not set in environment variables")
        if not user:
            raise ValueError("WORDPRESS_USER not set in environment variables")
        if not password:
            raise ValueError("WORDPRESS_PASS not set in environment variables")
        
        logger.info("WordPress credentials validated successfully")
        return url, user, password

    def _get_or_create_tag(self, tag_name: str, auth: HTTPBasicAuth) -> Optional[int]:
        """Get tag ID or create if it doesn't exist"""
        url, _, _ = self._get_credentials()
        base_url = url.split('/wp-json')[0]
        tags_url = f"{base_url}/wp-json/wp/v2/tags"
        
        # First try to find existing tag
        search_params = {'search': tag_name}
        response = requests.get(tags_url, params=search_params, auth=auth)
        
        if response.ok:
            existing_tags = response.json()
            if existing_tags:
                return existing_tags[0]['id']
        
        # Create new tag if not found
        payload = {'name': tag_name}
        response = requests.post(tags_url, json=payload, auth=auth)
        
        if response.ok:
            new_tag = response.json()
            return new_tag['id']
        else:
            logger.warning(f"Failed to create tag '{tag_name}': {response.text}")
            return None

    def _validate_response(self, response: requests.Response) -> Dict[str, Any]:
        """Validate the WordPress API response"""
        try:
            if not response.ok:
                response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Invalid response format")
                
            if 'id' not in data:
                raise ValueError("Post ID not found in response")
                
            return data
            
        except requests.exceptions.JSONDecodeError:
            raise ValueError(f"Invalid JSON response: {response.text}")
        except requests.exceptions.HTTPError:
            if response.status_code == 401:
                raise ValueError("Authentication failed. Check your WordPress credentials.")
            elif response.status_code == 404:
                raise ValueError("API endpoint not found. Check your WordPress URL.")
            else:
                raise ValueError(f"HTTP error {response.status_code}: {response.text}")

    def _run(self, title: str, content: str, tags: List[str], categories: List[int]) -> Dict[str, Any]:
        """Post content to WordPress and return the API response"""
        try:
            logger.info("WordPress Poster Tool received input")
            
            # Create post_data dictionary from parameters
            post_dict = {
                'title': str(title).strip(),
                'content': str(content),
                'tags': tags,
                'categories': categories
            }
            
            logger.debug(f"Post data:\n{json.dumps(post_dict, indent=2)}")
            
            # Additional validation
            if not post_dict['title']:
                raise ValueError("Title cannot be empty")
            if not post_dict['content']:
                raise ValueError("Content cannot be empty")
            if not isinstance(post_dict['categories'], list):
                raise ValueError("Categories must be a list")
            if not isinstance(post_dict['tags'], list):
                raise ValueError("Tags must be a list")
            
            # Get WordPress credentials
            url, user, password = self._get_credentials()
            auth = HTTPBasicAuth(str(user), str(password))
            
            # Process tags first to get their IDs
            tag_ids = []
            for tag_name in post_dict['tags']:
                tag_id = self._get_or_create_tag(tag_name, auth)
                if tag_id:
                    tag_ids.append(tag_id)
            
            # Format payload according to WordPress REST API requirements
            payload = {
                "title": {"raw": post_dict['title']},
                "content": {"raw": post_dict['content']},
                "status": "draft",
                "categories": post_dict['categories'],
                "tags": tag_ids
            }

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.info(f"Posting to WordPress: {payload['title']}")
            
            # Make the request with retry logic
            try:
                response = self._make_request_with_retry(
                    url=url,
                    auth=auth,
                    headers=headers,
                    payload=payload
                )
            except requests.RequestException as e:
                raise RuntimeError(f"Failed to connect to WordPress: {str(e)}")

            # Validate and return response
            result = self._validate_response(response)
            logger.info(f"Successfully created post {result.get('id')} at {result.get('link')}")
            return result

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error posting to WordPress: {str(e)}")
            raise RuntimeError(f"Failed to post to WordPress: {str(e)}")
