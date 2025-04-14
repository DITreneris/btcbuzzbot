"""
Ollama LLM Integration Module for BTCBuzzBot

This module provides the core functionality for interacting with Ollama for LLM-based
content generation. It handles API communication, error handling, and response processing.
"""

import requests
import time
import json
import logging
import os
from typing import Dict, Any, Optional, List, Tuple
from functools import lru_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('llm_integration')

class OllamaClient:
    """Client for interacting with Ollama API"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434", 
                 model: str = "mistral:7b",
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        """
        Initialize the Ollama client.
        
        Args:
            base_url: Base URL for Ollama API
            model: Model name to use
            max_retries: Maximum number of retries for failed API calls
            retry_delay: Delay between retries (with exponential backoff)
        """
        self.base_url = base_url
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.generate_endpoint = f"{base_url}/api/generate"
        
        # Validate connection when initializing
        try:
            self._check_connection()
            logger.info(f"Successfully connected to Ollama at {base_url}")
            logger.info(f"Using model: {model}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {str(e)}")
            logger.warning("Continuing with initialization, but API calls may fail")
            
    def _check_connection(self) -> bool:
        """Check if we can connect to the Ollama API"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            
            # Check if our model is available
            model_names = [m["name"] for m in models]
            if ":" in self.model:
                # Handle models with tags like mistral:7b
                model_name, _ = self.model.split(":", 1)
                return any(m.startswith(model_name) for m in model_names)
            else:
                return self.model in model_names
                
        except Exception as e:
            logger.error(f"Connection check failed: {str(e)}")
            return False
        
    def generate(self, 
                 prompt: str, 
                 max_tokens: int = 280,
                 temperature: float = 0.7,
                 top_p: float = 0.9,
                 stop_sequences: List[str] = None) -> Dict[str, Any]:
        """
        Generate text using Ollama API.
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (higher = more creative)
            top_p: Nucleus sampling parameter
            stop_sequences: Optional list of sequences to stop generation
            
        Returns:
            Dictionary containing the generated text and metadata
        """
        start_time = time.time()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if stop_sequences:
            payload["stop"] = stop_sequences
            
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.generate_endpoint, json=payload)
                response.raise_for_status()
                completion_time = time.time() - start_time
                
                result = response.json()
                
                # Process the response
                return {
                    "text": result["response"],
                    "completion_time": completion_time,
                    "model": self.model,
                    "success": True,
                    "prompt": prompt,
                    "parameters": {
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "top_p": top_p
                    }
                }
                
            except Exception as e:
                logger.error(f"Generation attempt {attempt+1} failed: {str(e)}")
                
                # If this was the last attempt, return error
                if attempt == self.max_retries - 1:
                    return {
                        "text": "",
                        "completion_time": time.time() - start_time,
                        "model": self.model,
                        "success": False,
                        "error": str(e),
                        "prompt": prompt
                    }
                
                # Otherwise wait and retry
                wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {wait_time:.2f} seconds...")
                time.sleep(wait_time)
    
    @lru_cache(maxsize=100)
    def cached_generate(self, 
                        prompt: str, 
                        max_tokens: int = 280,
                        temperature: float = 0.7,
                        top_p: float = 0.9) -> Dict[str, Any]:
        """
        Cached version of generate for frequently used prompts.
        Note: Only use for prompts that don't need to be dynamic.
        
        Args are the same as generate()
        """
        return self.generate(prompt, max_tokens, temperature, top_p)
    
    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama API"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return [model["name"] for model in response.json().get("models", [])]
        except Exception as e:
            logger.error(f"Failed to get available models: {str(e)}")
            return []
            
    def change_model(self, new_model: str) -> bool:
        """Change the current model"""
        if new_model == self.model:
            return True
            
        # Verify the model exists
        available_models = self.get_available_models()
        model_exists = new_model in available_models
        
        if ":" in new_model and not model_exists:
            # Check if base model exists for tagged models (e.g. mistral:7b)
            base_model = new_model.split(":", 1)[0]
            model_exists = any(m.startswith(base_model) for m in available_models)
            
        if not model_exists:
            logger.error(f"Model {new_model} not found in available models")
            return False
            
        # Update the model
        self.model = new_model
        logger.info(f"Changed model to {new_model}")
        return True


class ContentGenerator:
    """
    High-level content generator using Ollama LLM.
    This class handles prompt management, generation, and post-processing.
    """
    
    def __init__(self, 
                 ollama_client: OllamaClient,
                 max_length: int = 280,
                 default_temperature: float = 0.7):
        """
        Initialize the content generator.
        
        Args:
            ollama_client: Initialized OllamaClient instance
            max_length: Maximum length of generated content
            default_temperature: Default temperature for generation
        """
        self.client = ollama_client
        self.max_length = max_length
        self.default_temperature = default_temperature
        
    def generate_price_update(self, 
                              current_price: float, 
                              change_24h: float, 
                              market_trend: str) -> Dict[str, Any]:
        """
        Generate a price update post.
        
        Args:
            current_price: Current BTC price in USD
            change_24h: 24-hour price change percentage
            market_trend: Market trend description (bullish, bearish, neutral)
            
        Returns:
            Dictionary with generated content and metadata
        """
        # Format the price nicely
        formatted_price = f"${current_price:,.2f}"
        
        # Determine if price went up or down
        direction = "up" if change_24h > 0 else "down"
        
        # Create the prompt
        prompt = f"""Generate a short, engaging tweet about the current Bitcoin price.
Current price: {formatted_price}
24h change: {change_24h:.2f}% ({direction})
Market trend: {market_trend}

Make it informative but also add some personality. Include the price, mention the {direction}ward movement, and reflect the {market_trend} sentiment.
Keep it under 280 characters and include hashtags #Bitcoin #BTC at the end.

Tweet:"""

        # Generate the content
        result = self.client.generate(
            prompt=prompt,
            max_tokens=self.max_length,
            temperature=self.default_temperature
        )
        
        # Add context information to the result
        result["context"] = {
            "current_price": current_price,
            "change_24h": change_24h,
            "market_trend": market_trend
        }
        
        return result
        
    def generate_crypto_joke(self) -> Dict[str, Any]:
        """Generate a Bitcoin/crypto related joke"""
        prompt = """Generate a short, funny joke or pun related to Bitcoin or cryptocurrency. 
Make it witty, original, and suitable for Twitter (under 280 characters).
Include the hashtags #Bitcoin #CryptoHumor at the end.

Joke:"""

        return self.client.generate(
            prompt=prompt,
            max_tokens=self.max_length,
            temperature=0.8  # Slightly higher temperature for creativity
        )
        
    def generate_motivational_content(self, 
                                      current_price: float = None, 
                                      market_status: str = None) -> Dict[str, Any]:
        """Generate motivational content related to Bitcoin investing/holding"""
        context = ""
        if current_price and market_status:
            context = f"Current Bitcoin price is ${current_price:,.2f} and the market seems {market_status}. "
            
        prompt = f"""Generate a short, motivational message for Bitcoin investors and enthusiasts.
{context}Focus on long-term thinking, persistence, and the revolutionary potential of Bitcoin.
Make it inspiring but not overly hyped. Keep it under 280 characters total.
Include hashtags #Bitcoin #HODL at the end.

Motivational message:"""

        return self.client.generate(
            prompt=prompt,
            max_tokens=self.max_length,
            temperature=0.7
        )
        
    def validate_content(self, content: str) -> Tuple[bool, str]:
        """
        Validate generated content for various criteria.
        
        Args:
            content: The generated content to validate
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check length
        if len(content) > self.max_length:
            return False, f"Content exceeds maximum length ({len(content)} > {self.max_length})"
            
        # Check for common issues
        if "insert" in content.lower() or "your text here" in content.lower():
            return False, "Content contains placeholder text"
            
        # Check hashtag presence
        if "#" not in content:
            return False, "Content missing hashtags"
            
        # Check for empty/invalid responses    
        if len(content.strip()) < 10:
            return False, "Content too short or empty"
            
        return True, "Content valid"


def initialize_ollama(base_url: str = None, model: str = None) -> OllamaClient:
    """
    Initialize the Ollama client with environment variables or defaults.
    
    Args:
        base_url: Base URL for Ollama API (optional, overrides env var)
        model: Model to use (optional, overrides env var)
        
    Returns:
        Initialized OllamaClient
    """
    # Get configuration from environment variables or use defaults
    ollama_url = base_url or os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
    ollama_model = model or os.environ.get("OLLAMA_MODEL", "mistral:7b")
    
    # Create and return the client
    return OllamaClient(
        base_url=ollama_url,
        model=ollama_model
    )


# Initialize global client if module is imported directly
if __name__ != "__main__":
    try:
        # Only create the global client if environment variables are set
        if "OLLAMA_API_URL" in os.environ:
            client = initialize_ollama()
            content_generator = ContentGenerator(client)
            logger.info("Initialized global Ollama client and content generator")
    except Exception as e:
        logger.error(f"Failed to initialize global Ollama client: {str(e)}")
        logger.warning("Ollama integration will not be available")


# Example usage
if __name__ == "__main__":
    # This is just for testing the module directly
    client = initialize_ollama()
    generator = ContentGenerator(client)
    
    # Test price update generation
    price_update = generator.generate_price_update(
        current_price=43500.75,
        change_24h=2.5,
        market_trend="bullish"
    )
    
    if price_update["success"]:
        print("✅ Price Update Generated:")
        print(price_update["text"])
        print(f"Generation time: {price_update['completion_time']:.2f}s")
    else:
        print("❌ Price Update Generation Failed:")
        print(price_update["error"])
        
    # Test joke generation
    joke = generator.generate_crypto_joke()
    
    if joke["success"]:
        print("\n✅ Crypto Joke Generated:")
        print(joke["text"])
        print(f"Generation time: {joke['completion_time']:.2f}s")
    else:
        print("\n❌ Joke Generation Failed:")
        print(joke["error"]) 