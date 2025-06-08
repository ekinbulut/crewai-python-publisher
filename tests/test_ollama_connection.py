import requests
import pytest
from langchain_ollama import OllamaLLM
from logger import setup_logger

logger = setup_logger()

def test_ollama_connection():
    logger.info("Testing Ollama connection...")

    try:
        response = requests.get('http://localhost:11434/api/version', timeout=3)
    except requests.exceptions.ConnectionError:
        pytest.skip("Ollama API is not available")

    assert response.status_code == 200

    response = requests.post('http://localhost:11434/api/show', json={'name': 'mistral:7b'})
    assert response.status_code == 200

    llm = OllamaLLM(model="mistral:7b")
    result = llm.invoke("Return only the word 'success' if you can read this.")
    assert 'success' in result.lower()

