"""
LLM Client module for abstracting interactions with different LLM providers.
Supports Google Gemini and OpenAI models with a unified interface.
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from enum import Enum
import google.generativeai as genai
from loguru import logger
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    GEMINI = "gemini"
    OPENAI = "openai"


class LLMConfig(BaseModel):
    """Configuration for LLM clients"""
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1.0, ge=0, le=1)
    top_k: Optional[int] = Field(default=1, ge=1)
    max_tokens: Optional[int] = Field(default=8192, ge=1)
    model_name: str = Field(...)
    api_key: Optional[str] = Field(default=None)
    max_retries: int = Field(default=3, ge=1)
    retry_delay: int = Field(default=5, ge=1)


class LLMResponse(BaseModel):
    """Standardized LLM response"""
    content: str
    model: str
    provider: LLMProvider
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None


class LLMClientBase(ABC):
    """Abstract base class for LLM clients"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.usage_stats = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_requests": 0,
            "failed_requests": 0
        }
    
    @abstractmethod
    def generate(self, prompt: str) -> LLMResponse:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def validate_api_key(self) -> bool:
        """Validate the API key"""
        pass
    
    def get_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics"""
        return self.usage_stats.copy()
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.usage_stats = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_requests": 0,
            "failed_requests": 0
        }


class GeminiClient(LLMClientBase):
    """Google Gemini LLM client implementation"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        
        # Get API key from config or environment
        api_key = config.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("Gemini API key not found in config or environment variables")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Generation config
        self.generation_config = {
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
        }
        if config.max_tokens:
            self.generation_config["max_output_tokens"] = config.max_tokens
        
        # Safety settings
        self.safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        # Initialize model
        self.model = genai.GenerativeModel(
            model_name=config.model_name,
            generation_config=self.generation_config,
            safety_settings=self.safety_settings
        )
        
        logger.info(f"Initialized Gemini client with model: {config.model_name}")
    
    def generate(self, prompt: str) -> LLMResponse:
        """Generate a response from Gemini"""
        self.usage_stats["total_requests"] += 1
        
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Sending request to Gemini (attempt {attempt + 1}/{self.config.max_retries})")
                
                response = self.model.generate_content(prompt)
                
                if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    content = response.candidates[0].content.parts[0].text
                    
                    # Update usage stats (Gemini doesn't provide token counts directly)
                    # This is an estimation
                    estimated_prompt_tokens = len(prompt.split()) * 1.3
                    estimated_completion_tokens = len(content.split()) * 1.3
                    
                    self.usage_stats["prompt_tokens"] += int(estimated_prompt_tokens)
                    self.usage_stats["completion_tokens"] += int(estimated_completion_tokens)
                    self.usage_stats["total_tokens"] += int(estimated_prompt_tokens + estimated_completion_tokens)
                    
                    return LLMResponse(
                        content=content,
                        model=self.config.model_name,
                        provider=LLMProvider.GEMINI,
                        usage={
                            "prompt_tokens": int(estimated_prompt_tokens),
                            "completion_tokens": int(estimated_completion_tokens),
                            "total_tokens": int(estimated_prompt_tokens + estimated_completion_tokens)
                        },
                        finish_reason="stop"
                    )
                elif response.prompt_feedback:
                    error_msg = f"Generation blocked: {response.prompt_feedback}"
                    logger.error(error_msg)
                    if attempt < self.config.max_retries - 1:
                        time.sleep(self.config.retry_delay)
                        continue
                    else:
                        self.usage_stats["failed_requests"] += 1
                        raise ValueError(error_msg)
                else:
                    logger.warning("Empty or unexpected response from Gemini")
                    if attempt < self.config.max_retries - 1:
                        time.sleep(self.config.retry_delay)
                        continue
                    else:
                        self.usage_stats["failed_requests"] += 1
                        raise ValueError("Empty response from Gemini")
                        
            except Exception as e:
                logger.error(f"Error in Gemini generation (attempt {attempt + 1}): {e}")
                
                # Handle rate limiting
                if "429" in str(e) or "rate limit" in str(e).lower() or "exhausted" in str(e).lower():
                    wait_time = self.config.retry_delay * (attempt + 2)
                    logger.warning(f"Rate limit hit, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                elif attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    self.usage_stats["failed_requests"] += 1
                    raise
        
        self.usage_stats["failed_requests"] += 1
        raise Exception(f"Failed to generate response after {self.config.max_retries} attempts")
    
    def validate_api_key(self) -> bool:
        """Validate the Gemini API key"""
        try:
            # Try a simple generation to validate the key
            test_prompt = "Say 'test' if you can read this."
            response = self.model.generate_content(test_prompt)
            return bool(response.candidates)
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False


class OpenAIClient(LLMClientBase):
    """OpenAI LLM client implementation"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        
        try:
            import openai
        except ImportError:
            raise ImportError("OpenAI package not installed. Install with: pip install openai")
        
        # Get API key from config or environment
        api_key = config.api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found in config or environment variables")
        
        self.client = openai.OpenAI(api_key=api_key)
        logger.info(f"Initialized OpenAI client with model: {config.model_name}")
    
    def generate(self, prompt: str) -> LLMResponse:
        """Generate a response from OpenAI"""
        self.usage_stats["total_requests"] += 1
        
        for attempt in range(self.config.max_retries):
            try:
                logger.debug(f"Sending request to OpenAI (attempt {attempt + 1}/{self.config.max_retries})")
                
                response = self.client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.temperature,
                    top_p=self.config.top_p,
                    max_tokens=self.config.max_tokens
                )
                
                content = response.choices[0].message.content
                
                # Update usage stats
                if response.usage:
                    self.usage_stats["prompt_tokens"] += response.usage.prompt_tokens
                    self.usage_stats["completion_tokens"] += response.usage.completion_tokens
                    self.usage_stats["total_tokens"] += response.usage.total_tokens
                
                return LLMResponse(
                    content=content,
                    model=response.model,
                    provider=LLMProvider.OPENAI,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                        "total_tokens": response.usage.total_tokens if response.usage else 0
                    },
                    finish_reason=response.choices[0].finish_reason
                )
                
            except Exception as e:
                logger.error(f"Error in OpenAI generation (attempt {attempt + 1}): {e}")
                
                # Handle rate limiting
                if "rate limit" in str(e).lower():
                    wait_time = self.config.retry_delay * (attempt + 2)
                    logger.warning(f"Rate limit hit, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                elif attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    self.usage_stats["failed_requests"] += 1
                    raise
        
        self.usage_stats["failed_requests"] += 1
        raise Exception(f"Failed to generate response after {self.config.max_retries} attempts")
    
    def validate_api_key(self) -> bool:
        """Validate the OpenAI API key"""
        try:
            # Try to list models to validate the key
            self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False


class LLMClientFactory:
    """Factory for creating LLM clients"""
    
    @staticmethod
    def create(provider: LLMProvider, config: LLMConfig) -> LLMClientBase:
        """Create an LLM client based on the provider"""
        if provider == LLMProvider.GEMINI:
            return GeminiClient(config)
        elif provider == LLMProvider.OPENAI:
            return OpenAIClient(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    @staticmethod
    def create_from_env(provider: Optional[LLMProvider] = None) -> LLMClientBase:
        """Create an LLM client from environment variables"""
        # Determine provider if not specified
        if not provider:
            if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
                provider = LLMProvider.GEMINI
            # elif os.getenv("GOOGLE_API_KEY"):
            #     provider = LLMProvider.OPENAI
            else:
                raise ValueError("No LLM API keys found in environment variables")
        
        # Create config based on provider
        if provider == LLMProvider.GEMINI:
            config = LLMConfig(
                model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest"),
                temperature=float(os.getenv("AGENT_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("AGENT_MAX_TOKENS", "8192")),
                max_retries=int(os.getenv("AGENT_MAX_RETRIES", "3")),
                retry_delay=int(os.getenv("AGENT_RETRY_DELAY", "5"))
            )
        else:  # OpenAI
            config = LLMConfig(
                model_name=os.getenv("OPENAI_MODEL", "gpt-4"),
                temperature=float(os.getenv("AGENT_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("AGENT_MAX_TOKENS", "8192")),
                max_retries=int(os.getenv("AGENT_MAX_RETRIES", "3")),
                retry_delay=int(os.getenv("AGENT_RETRY_DELAY", "5"))
            )
        
        return LLMClientFactory.create(provider, config) 