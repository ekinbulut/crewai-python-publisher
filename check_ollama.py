import requests
from logger import setup_logger

logger = setup_logger()

def check_ollama():
    try:
        response = requests.get('http://localhost:11434/api/version')
        if response.status_code == 200:
            logger.info("Ollama is running")
            return True
        logger.error("Ollama returned unexpected status code")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("Ollama is not running - Please start Ollama first")
        return False
    except Exception as e:
        logger.error(f"Error checking Ollama: {str(e)}")
        return False
