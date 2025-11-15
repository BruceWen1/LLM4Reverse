# -*- coding: utf-8 -*-
"""
config.py
Project Configuration Module
=====================

Project configuration and environment defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

try:
	from dotenv import load_dotenv  # type: ignore
	# Load environment variables from a .env file if present.
	# Do not override existing process envs.
	load_dotenv(override=False)
except Exception:
	# If python-dotenv is unavailable or fails, continue silently.
	pass

@dataclass(frozen=True)
class OpenAIConfig:
	"""
	Configuration for OpenAI-compatible chat models.
	"""
	api_key: Optional[str]  # API key
	base_url: Optional[str]  # API base URL
	default_model: Optional[str]  # Default model name
	temperature: float  # Sampling temperature


def load_openai_config() -> OpenAIConfig:
	"""
	Load OpenAI configuration from environment variables.

	Returns:
		OpenAIConfig: Configured OpenAI config object.
	"""
	return OpenAIConfig(
		api_key=os.getenv("API_KEY"),
		base_url=os.getenv("BASE_URL"),
		default_model=os.getenv("MODEL"),
		temperature=float(os.getenv("TEMPERATURE", "0.0")),
	)


