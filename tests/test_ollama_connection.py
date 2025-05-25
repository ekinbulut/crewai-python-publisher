import requests
from langchain_ollama import OllamaLLM
from logger import setup_logger
import sys

logger = setup_logger()

def test_ollama_connection():
    logger.info("Testing Ollama connection...")
    
    # Test 1: Basic Ollama API connection
    try:
        response = requests.get('http://localhost:11434/api/version')
        if response.status_code == 200:
            logger.info(f"Ollama API is running. Version: {response.json().get('version')}")
        else:
            logger.error(f"Ollama API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to Ollama API")
        return False
        
    # Test 2: Model availability
    try:
        response = requests.post('http://localhost:11434/api/show', json={'name': 'mistral:7b'})
        if response.status_code == 200:
            logger.info("Mistral model is available")
        else:
            logger.error("Mistral model not found")
            return False
    except Exception as e:
        logger.error(f"Error checking model availability: {str(e)}")
        return False
        
    # Test 3: LangChain Ollama integration
    try:
        llm = OllamaLLM(model="mistral:7b")
        test_prompt = "Return only the word 'success' if you can read this."
        result = llm.invoke(test_prompt)
        logger.info(f"LangChain-Ollama test result: {result}")
        if 'success' in result.lower():
            logger.info("LangChain-Ollama integration working")
        else:
            logger.warning("LangChain-Ollama response unexpected")
            return False
    except Exception as e:
        logger.error(f"Error testing LangChain-Ollama integration: {str(e)}")
        return False
        
    logger.info("All Ollama connection tests passed!")
    return True

if __name__ == "__main__":
    success = test_ollama_connection()
    if not success:
        logger.error("Ollama connection test failed")
        sys.exit(1)
    logger.info("Ollama is ready for CrewAI")
