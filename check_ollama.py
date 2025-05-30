import requests
import time
from logger import setup_logger

logger = setup_logger()

def check_ollama(max_retries=3, retry_delay=5):
    """Check Ollama availability with retries
    
    Args:
        max_retries (int): Maximum number of connection attempts
        retry_delay (int): Seconds to wait between retries
    """
    for attempt in range(max_retries):
        try:
            response = requests.get('http://localhost:11434/api/version')
            if response.status_code == 200:
                logger.info(f"Ollama is running (attempt {attempt + 1}/{max_retries})")
                return True
            
            logger.warning(f"Ollama returned unexpected status code (attempt {attempt + 1}/{max_retries})")
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"Ollama connection failed (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            logger.error(f"Error checking Ollama: {str(e)} (attempt {attempt + 1}/{max_retries})")
        
        if attempt < max_retries - 1:
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    logger.error("Failed to connect to Ollama after all retries")
    return False
