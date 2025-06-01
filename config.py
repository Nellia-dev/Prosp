"""
Configuration management system for Nellia Prospector
Centralized configuration with environment variable support and validation.
"""

import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class LLMConfig:
    """LLM configuration settings"""
    provider: str = "gemini"  # gemini, openai
    model_name: str = "gemini-1.5-flash-latest"
    temperature: float = 0.7
    max_tokens: int = 8192
    max_retries: int = 3
    retry_delay: int = 5
    api_key: Optional[str] = None
    
    def __post_init__(self):
        if not self.api_key:
            if self.provider == "gemini":
                self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            elif self.provider == "openai":
                self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError(f"API key not found for provider: {self.provider}")

@dataclass
class ProcessingConfig:
    """Processing pipeline configuration"""
    max_text_length: int = 15000
    max_leads_per_batch: int = 100
    skip_failed_extractions: bool = False
    enable_enhanced_processing: bool = True
    enable_tavily_enrichment: bool = True
    processing_timeout_seconds: int = 300
    
@dataclass
class TavilyConfig:
    """Tavily API configuration"""
    api_key: Optional[str] = None
    max_results: int = 3
    max_queries: int = 3
    timeout_seconds: int = 20
    
    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("TAVILY_API_KEY")

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = "logs/nellia_prospector.log"
    enable_rich: bool = True
    max_file_size: str = "10 MB"
    retention_days: int = 30

@dataclass
class ExportConfig:
    """Export and output configuration"""
    default_output_dir: str = "outputs"
    default_export_format: str = "json"
    enable_csv_export: bool = True
    enable_excel_export: bool = False
    max_export_records: int = 10000

@dataclass
class BusinessConfig:
    """Business logic configuration"""
    product_service_context: str = "Soluções de IA para otimização de processos de vendas e geração de leads B2B"
    competitors_list: str = ""
    target_roi_increase: float = 5.27  # 527%
    min_relevance_score: float = 0.7
    min_qualification_score: float = 0.6
    brazilian_market_focus: bool = True

@dataclass
class NelliaProspectorConfig:
    """Main configuration class"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    tavily: TavilyConfig = field(default_factory=TavilyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    business: BusinessConfig = field(default_factory=BusinessConfig)
    
    # Runtime configuration
    debug_mode: bool = False
    development_mode: bool = False
    metrics_enabled: bool = True
    
    def __post_init__(self):
        # Override with environment variables if present
        self._load_from_environment()
        
        # Validate configuration
        self._validate_config()
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        
        # LLM configuration
        if os.getenv("LLM_PROVIDER"):
            self.llm.provider = os.getenv("LLM_PROVIDER")
        if os.getenv("LLM_MODEL"):
            self.llm.model_name = os.getenv("LLM_MODEL")
        if os.getenv("LLM_TEMPERATURE"):
            self.llm.temperature = float(os.getenv("LLM_TEMPERATURE"))
        if os.getenv("LLM_MAX_TOKENS"):
            self.llm.max_tokens = int(os.getenv("LLM_MAX_TOKENS"))
        
        # Processing configuration
        if os.getenv("MAX_LEADS_PER_BATCH"):
            self.processing.max_leads_per_batch = int(os.getenv("MAX_LEADS_PER_BATCH"))
        if os.getenv("SKIP_FAILED_EXTRACTIONS"):
            self.processing.skip_failed_extractions = os.getenv("SKIP_FAILED_EXTRACTIONS").lower() == "true"
        if os.getenv("ENABLE_ENHANCED_PROCESSING"):
            self.processing.enable_enhanced_processing = os.getenv("ENABLE_ENHANCED_PROCESSING").lower() == "true"
        
        # Logging configuration
        if os.getenv("LOG_LEVEL"):
            self.logging.level = os.getenv("LOG_LEVEL")
        if os.getenv("LOG_TO_FILE"):
            self.logging.log_to_file = os.getenv("LOG_TO_FILE").lower() == "true"
        
        # Business configuration
        if os.getenv("PRODUCT_SERVICE_CONTEXT"):
            self.business.product_service_context = os.getenv("PRODUCT_SERVICE_CONTEXT")
        if os.getenv("COMPETITORS_LIST"):
            self.business.competitors_list = os.getenv("COMPETITORS_LIST")
        
        # Runtime flags
        if os.getenv("DEBUG_MODE"):
            self.debug_mode = os.getenv("DEBUG_MODE").lower() == "true"
        if os.getenv("DEVELOPMENT_MODE"):
            self.development_mode = os.getenv("DEVELOPMENT_MODE").lower() == "true"
    
    def _validate_config(self):
        """Validate configuration values"""
        errors = []
        
        # Validate LLM configuration
        if self.llm.provider not in ["gemini", "openai"]:
            errors.append(f"Invalid LLM provider: {self.llm.provider}")
        
        if not (0.0 <= self.llm.temperature <= 2.0):
            errors.append(f"LLM temperature must be between 0.0 and 2.0: {self.llm.temperature}")
        
        # Validate processing configuration
        if self.processing.max_leads_per_batch <= 0:
            errors.append(f"Max leads per batch must be positive: {self.processing.max_leads_per_batch}")
        
        # Validate business configuration
        if not (0.0 <= self.business.min_relevance_score <= 1.0):
            errors.append(f"Min relevance score must be between 0.0 and 1.0: {self.business.min_relevance_score}")
        
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration specific to an agent"""
        base_config = {
            "llm_provider": self.llm.provider,
            "llm_model": self.llm.model_name,
            "temperature": self.llm.temperature,
            "max_tokens": self.llm.max_tokens,
            "product_service_context": self.business.product_service_context,
            "debug_mode": self.debug_mode
        }
        
        # Agent-specific configurations
        agent_configs = {
            "lead_intake": {
                "skip_failed_extractions": self.processing.skip_failed_extractions,
                "max_text_length": self.processing.max_text_length
            },
            "lead_analysis": {
                "product_service_context": self.business.product_service_context
            },
            "enhanced_processor": {
                "tavily_api_key": self.tavily.api_key,
                "competitors_list": self.business.competitors_list,
                "enable_tavily": self.processing.enable_tavily_enrichment
            }
        }
        
        if agent_name in agent_configs:
            base_config.update(agent_configs[agent_name])
        
        return base_config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "llm": {
                "provider": self.llm.provider,
                "model_name": self.llm.model_name,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens
            },
            "processing": {
                "max_text_length": self.processing.max_text_length,
                "max_leads_per_batch": self.processing.max_leads_per_batch,
                "skip_failed_extractions": self.processing.skip_failed_extractions,
                "enable_enhanced_processing": self.processing.enable_enhanced_processing,
                "enable_tavily_enrichment": self.processing.enable_tavily_enrichment
            },
            "business": {
                "product_service_context": self.business.product_service_context,
                "target_roi_increase": self.business.target_roi_increase,
                "min_relevance_score": self.business.min_relevance_score
            },
            "runtime": {
                "debug_mode": self.debug_mode,
                "development_mode": self.development_mode,
                "metrics_enabled": self.metrics_enabled
            }
        }


# Global configuration instance
_config_instance: Optional[NelliaProspectorConfig] = None

def get_config() -> NelliaProspectorConfig:
    """Get the global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = NelliaProspectorConfig()
    return _config_instance

def reload_config() -> NelliaProspectorConfig:
    """Reload configuration from environment"""
    global _config_instance
    _config_instance = NelliaProspectorConfig()
    return _config_instance

def configure_from_file(config_file: str) -> NelliaProspectorConfig:
    """Load configuration from file (YAML or JSON)"""
    import json
    import yaml
    
    config_path = Path(config_file)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            config_data = yaml.safe_load(f)
        else:
            config_data = json.load(f)
    
    # Override environment variables with file data
    for section, values in config_data.items():
        if isinstance(values, dict):
            for key, value in values.items():
                env_key = f"{section.upper()}_{key.upper()}"
                os.environ[env_key] = str(value)
    
    return reload_config()

# Helper functions for common configuration patterns
def is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    return get_config().debug_mode

def is_development_mode() -> bool:
    """Check if development mode is enabled"""
    return get_config().development_mode

def get_llm_config() -> LLMConfig:
    """Get LLM configuration"""
    return get_config().llm

def get_processing_config() -> ProcessingConfig:
    """Get processing configuration"""
    return get_config().processing

def get_business_config() -> BusinessConfig:
    """Get business configuration"""
    return get_config().business