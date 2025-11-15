# -*- coding: utf-8 -*-
"""
client.py
LLM Module
=====================

OpenAI client wrapper for Chat calls.
"""

import logging
import os
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# Load .env variables at import time
load_dotenv()

# Monkey-patch to fix custom API gateway response format compatibility
def _patch_langchain_openai():
    """
    Patch langchain_openai to handle custom API gateway responses that return strings
    instead of objects with model_dump() method.
    
    The issue occurs in _create_chat_result where it expects:
    `response if isinstance(response, dict) else response.model_dump()`
    but custom APIs may return a string instead of an object.
    """
    try:
        from langchain_openai.chat_models.base import ChatOpenAI as BaseChatOpenAI
        original_create_chat_result = BaseChatOpenAI._create_chat_result
        
        def patched_create_chat_result(self, response, generation_info=None):
            """Patched version that handles string responses from custom API gateways."""
            # Check if response is a string (custom API gateway issue)
            if isinstance(response, str):
                logger.warning("Custom API gateway returned string response, attempting to parse...")
                import json
                try:
                    # Try to parse as JSON
                    response_dict = json.loads(response)
                    # Create a mock object with model_dump method that returns the dict
                    class MockResponse:
                        def __init__(self, data):
                            self._data = data
                        def model_dump(self):
                            return self._data
                        def __getattr__(self, name):
                            # Allow access to dict keys as attributes
                            return self._data.get(name)
                    response = MockResponse(response_dict)
                    logger.debug("Successfully converted string response to mock object")
                except (json.JSONDecodeError, Exception) as parse_err:
                    logger.error("Failed to parse custom API response as JSON: %s", parse_err)
                    logger.debug("Response content (first 500 chars): %s", response[:500])
                    # Re-raise the original error format
                    raise AttributeError("'str' object has no attribute 'model_dump'") from parse_err
            
            # Call original method (will handle dict or object with model_dump)
            try:
                return original_create_chat_result(self, response, generation_info)
            except AttributeError as e:
                if "'str' object has no attribute 'model_dump'" in str(e):
                    # If we still get this error, log and re-raise with more context
                    logger.error("Failed to handle response format: %s", type(response))
                    if isinstance(response, str):
                        logger.error("Response is still a string after parsing attempt: %s", response[:200])
                    raise
                raise
        
        # Apply the patch
        BaseChatOpenAI._create_chat_result = patched_create_chat_result
        logger.debug("Applied langchain_openai compatibility patch for custom API gateways")
    except Exception as e:
        logger.warning("Failed to apply langchain_openai patch: %s", e)
        import traceback
        logger.debug("Patch error traceback: %s", traceback.format_exc())

# Apply patch at module import time
_patch_langchain_openai()

def get_chat_llm(model_name: Optional[str] = None, temperature: float = 0.0) -> ChatOpenAI:
    """
    Create and return a ChatOpenAI instance with configured settings.

    Environment Variables:
        API_KEY: API key for OpenAI-compatible provider.
        BASE_URL: (optional) Override API base URL.
        MODEL: Default model if model_name not provided.

    Args:
        model_name (str): OpenAI model name.
        temperature (float): Sampling temperature.

    Returns:
        ChatOpenAI: Configured chat LLM client.
    """
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL", None)
    if not api_key:
        logger.error("API_KEY is not set")
        raise RuntimeError("Missing API_KEY")
    if not model_name:
        model_name = os.getenv("MODEL")
    if not model_name:
        logger.error("MODEL is not set and no model_name provided")
        raise RuntimeError("Missing MODEL")
    
    # Build kwargs for ChatOpenAI
    kwargs = {
        "model": model_name,
        "temperature": temperature,
        "api_key": api_key,
        "streaming": False,  # Disable streaming for agent compatibility
    }
    
    # Only add base_url if it's provided (some custom APIs may have compatibility issues)
    if base_url:
        kwargs["base_url"] = base_url
        # For custom API gateways, try to ensure compatibility
        # Add timeout and other settings that might help
        kwargs["timeout"] = 60.0
        logger.info("Using custom base_url: %s", base_url)
    
    # Instantiate LangChain ChatOpenAI (0.3.x style kwargs)
    try:
        client = ChatOpenAI(**kwargs)
        logger.info("Initialized ChatOpenAI: model=%s, temperature=%f, base_url=%s", 
                   model_name, temperature, base_url or "[default]")
        return client
    except Exception as e:
        logger.error("Failed to initialize ChatOpenAI: %s", e)
        # If initialization fails, try without base_url as fallback
        if base_url:
            logger.warning("Retrying without base_url...")
            kwargs.pop("base_url", None)
            client = ChatOpenAI(**kwargs)
            logger.info("Initialized ChatOpenAI (fallback, no base_url): model=%s", model_name)
            return client
        raise
