from langchain_community.llms.ollama import Ollama
from typing import Any, List, Mapping, Optional
import logging

logger = logging.getLogger(__name__)

class CustomOllamaLLM(Ollama):
    def __init__(
        self,
        model: str = "mistral:7b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        timeout: float = 120,
        **kwargs: Any,
    ) -> None:
        """Initialize the Ollama LLM."""
        super().__init__(
            model=model,
            base_url=base_url,
            temperature=temperature,
            timeout=timeout,
            **kwargs
        )
        logger.info(f"Initialized Ollama LLM with model {model}")
        
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        """Execute the LLM call."""
        try:
            response = super()._call(prompt, stop=stop, run_manager=run_manager, **kwargs)
            return response
        except Exception as e:
            logger.error(f"Error calling Ollama: {str(e)}")
            raise

    def _identifying_params(self) -> Mapping[str, Any]:
        """Get parameters used to identify this LLM."""
        return {
            "name": "CustomOllama",
            "model": self.model,
            "temperature": self.temperature
        }
