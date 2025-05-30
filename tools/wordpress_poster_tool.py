from crewai.tools import BaseTool
from pydantic import Field
import requests
import os
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from logger import setup_logger
from typing import Dict, Any, List, Tuple, Optional, Union
from urllib.parse import urljoin, urlparse
import re
import time

logger = setup_logger()

class WordPressPosterTool(BaseTool):
    name: str = Field(default="wordpress_poster")
    description: str = Field(default="Posts content to a WordPress blog using the REST API")
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
                    timeout=30  # Add explicit timeout
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

    def _create_tag(self, tag_name: str) -> int:
        """Create a new tag and return its ID"""
        url, user, password = self._get_credentials()
        api_url = f"{url.rsplit('/posts', 1)[0]}/tags"
        
        payload = {
            "name": tag_name,
            "description": ""  # Optional description
        }
        
        try:
            response = requests.post(
                api_url,
                auth=HTTPBasicAuth(user, password),
                headers={'Content-Type': 'application/json'},
                json=payload
            )
            
            if response.ok:
                data = response.json()
                return data.get('id')
            elif response.status_code == 400 and 'existing' in response.text.lower():
                # Tag might already exist, try to fetch it
                return self._get_tag_id(tag_name)
            else:
                logger.warning(f"Failed to create tag '{tag_name}': {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating tag '{tag_name}': {str(e)}")
            return None
            
    def _get_tag_id(self, tag_name: str) -> Optional[int]:
        """Get the ID of an existing tag by name"""
        url, user, password = self._get_credentials()
        api_url = f"{url.rsplit('/posts', 1)[0]}/tags"
        
        try:
            response = requests.get(
                f"{api_url}?search={tag_name}",
                auth=HTTPBasicAuth(user, password)
            )
            
            if response.ok:
                tags = response.json()
                for tag in tags:
                    if tag.get('name', '').lower() == tag_name.lower():
                        return tag.get('id')
            return None
            
        except Exception as e:
            logger.error(f"Error fetching tag '{tag_name}': {str(e)}")
            return None
            
    def _handle_tags(self, tag_names: List[str]) -> List[int]:
        """Convert tag names to tag IDs, creating new tags if necessary"""
        tag_ids = []
        for tag_name in tag_names:
            # Try to get existing tag ID
            tag_id = self._get_tag_id(tag_name)
            if tag_id is None:
                # Create new tag if it doesn't exist
                tag_id = self._create_tag(tag_name)
            if tag_id:
                tag_ids.append(tag_id)
        return tag_ids

    def _get_credentials(self) -> Tuple[str, str, str]:
        """Get and validate WordPress credentials"""
        # Ensure environment variables are loaded
        load_dotenv()
        
        # Get credentials from environment
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

    def _get_or_create_tag(self, tag_name: str, auth: Tuple[str, str]) -> int:
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

    def _handle_tags(self, post_id: int, tag_names: List[str], auth: Tuple[str, str]) -> None:
        """Process tags for a post, creating them if needed"""
        if not tag_names:
            return
        
        tag_ids = []
        for tag_name in tag_names:
            tag_id = self._get_or_create_tag(tag_name, auth)
            if tag_id:
                tag_ids.append(tag_id)
        
        if tag_ids:
            url, _, _ = self._get_credentials()
            base_url = url.split('/wp-json')[0]
            update_url = f"{base_url}/wp-json/wp/v2/posts/{post_id}"
            
            response = requests.post(
                update_url,
                json={'tags': tag_ids},
                auth=auth
            )
            
            if not response.ok:
                logger.warning(f"Failed to update post tags: {response.text}")

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
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise ValueError("Authentication failed. Check your WordPress credentials.")
            elif response.status_code == 404:
                raise ValueError("API endpoint not found. Check your WordPress URL.")
            else:
                raise ValueError(f"HTTP error {response.status_code}: {response.text}")

    def _run(self, post_data: Any) -> Dict[str, Any]:
        """Post content to WordPress and return the API response"""
        try:
            logger.info("WordPress Poster Tool received input")
            logger.debug(f"Raw post data:\n{json.dumps(post_data, indent=2)}")
            
            # Ensure we have a dictionary
            if not isinstance(post_data, dict):
                raise ValueError("Input must be a dictionary")
            
            # Verify all required fields
            required_fields = ['title', 'content', 'tags', 'categories']
            if not all(k in post_data for k in required_fields):
                missing = [k for k in required_fields if k not in post_data]
                raise ValueError(f"Missing required fields: {', '.join(missing)}")
            
            # Clean and validate the data
            post_dict = {
                'title': str(post_data['title']).strip(),  # Ensure title is a clean string
                'content': str(post_data['content']),
                'categories': post_data['categories'],
                'tags': post_data['tags']
            }
            
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
            
            # Use the URL as is since it already contains the full API endpoint
            api_url = url
            
            # Format payload according to WordPress REST API requirements
            payload = {
                "title": post_dict['title'],
                "content": post_dict['content'],
                "status": "draft",  # Always create as draft first
                "categories": post_dict['categories']
                # Tags will be handled separately after post creation
            }
            
            # Make sure title and content are properly formatted for the API
            if isinstance(payload["title"], str):
                payload["title"] = {"raw": payload["title"]}
            if isinstance(payload["content"], str):
                payload["content"] = {"raw": payload["content"]}

            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            logger.info(f"Posting to WordPress: {payload['title']}")
            
            # Make the request
            try:
                response = requests.post(
                    api_url,
                    auth=HTTPBasicAuth(str(user), str(password)),  # Ensure strings for auth
                    headers=headers,
                    json=payload,
                    verify=True
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
