import pytest
import sys
import os
from dotenv import load_dotenv
from custom_ollama import CustomOllamaLLM

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(scope="session")
def ollama_client():
    """Fixture to provide a shared Ollama client instance."""
    load_dotenv()
    return CustomOllamaLLM(model="ollama/mistral:7b", base_url="http://localhost:11434")

@pytest.fixture(scope="session")
def test_env():
    """Fixture to set up test environment variables."""
    load_dotenv()
    return {
        "WORDPRESS_URL": os.getenv("WORDPRESS_URL"),
        "WORDPRESS_USER": os.getenv("WORDPRESS_USER"),
        "WORDPRESS_PASS": os.getenv("WORDPRESS_PASS")
    }
