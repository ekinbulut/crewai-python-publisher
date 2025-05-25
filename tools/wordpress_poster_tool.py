from crewai.tools import BaseTool
from pydantic import Field
import requests
import os
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from logger import setup_logger
from typing import Dict, Any

logger = setup_logger()
load_dotenv()

class WordPressPosterTool(BaseTool):
    name: str = Field(default="wordpress_poster")
    description: str = Field(default="Posts content to a WordPress blog using the REST API")

    def _validate_response(self, response: requests.Response) -> Dict[str, Any]:
        """Validate the WordPress API response"""
        try:
            response.raise_for_status()
            data = response.json()
            if 'id' not in data:
                raise ValueError("Post ID not found in response")
            return data
        except requests.exceptions.JSONDecodeError:
            raise ValueError(f"Invalid JSON response: {response.text}")
        except requests.exceptions.HTTPError as e:
            raise ValueError(f"HTTP error occurred: {str(e)}\nResponse: {response.text}")

    def _run(self, post_data: str) -> str:
        try:
            logger.info("WordPress Poster Tool received input")
            logger.debug(f"Raw post data:\n{post_data}")
            
            # Parse input
            lines = post_data.split("\n", 1)
            if not lines:
                raise ValueError("Empty post data provided")
            logger.info("Parsed post data into title and content")
            
            title = lines[0].strip()
            content = lines[1].strip() if len(lines) > 1 else ""
            
            if not title:
                raise ValueError("Post title cannot be empty")
            
            url = os.getenv("WORDPRESS_URL")
            token = os.getenv("WORDPRESS_TOKEN")
            user = os.getenv("WORDPRESS_USER")
            password = os.getenv("WORDPRESS_PASS")

            if not url:
                raise ValueError("WORDPRESS_URL not set in .env file")

            logger.info(f"Preparing to post article: {title}")
            logger.debug(f"Post URL: {url}")

            payload = {
                "title": title,
                "content": content,
                "status": "publish"
            }

            headers = {'Content-Type': 'application/json'}
            
            if token:
                headers['Authorization'] = f'Bearer {token}'
                logger.debug("Using token authentication")
                logger.info(f"Making POST request to {url}")
                response = requests.post(url, headers=headers, json=payload)
            elif user and password:
                logger.debug("Using basic authentication")
                logger.info(f"Making POST request to {url} with user {user}")
                logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")
                response = requests.post(
                    url,
                    auth=HTTPBasicAuth(user, password),
                    headers=headers,
                    json=payload
                )
            else:
                raise ValueError("No authentication credentials provided in .env file")

            # Validate and process response
            result = self._validate_response(response)
            post_id = result.get('id')
            post_url = result.get('link', 'URL not available')
            
            success_msg = f"Successfully posted article (ID: {post_id})\nURL: {post_url}"
            logger.info(success_msg)
            return success_msg

        except Exception as e:
            error_msg = f"Error posting to WordPress: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
