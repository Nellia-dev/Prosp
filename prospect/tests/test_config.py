"""
Unit tests for configuration management system
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from config import (
    NelliaProspectorConfig, LLMConfig, ProcessingConfig, TavilyConfig,
    LoggingConfig, ExportConfig, BusinessConfig, get_config, reload_config
)

class TestLLMConfig:
    """Test LLM configuration"""
    
    def test_default_config(self):
        config = LLMConfig()
        assert config.provider == "gemini"
        assert config.model_name == "gemini-1.5-flash-latest"
        assert config.temperature == 0.7
        assert config.max_tokens == 8192
        assert config.max_retries == 3
        assert config.retry_delay == 5
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    def test_gemini_api_key_from_env(self):
        config = LLMConfig()
        assert config.api_key == "test_key"
    
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "google_test_key"})
    def test_google_api_key_fallback(self):
        config = LLMConfig()
        assert config.api_key == "google_test_key"
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "openai_test_key"})
    def test_openai_api_key(self):
        config = LLMConfig(provider="openai")
        assert config.api_key == "openai_test_key"
    
    def test_missing_api_key_raises_error(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key not found"):
                LLMConfig()

class TestProcessingConfig:
    """Test processing configuration"""
    
    def test_default_config(self):
        config = ProcessingConfig()
        assert config.max_text_length == 15000
        assert config.max_leads_per_batch == 100
        assert config.skip_failed_extractions == False
        assert config.enable_enhanced_processing == True
        assert config.enable_tavily_enrichment == True
        assert config.processing_timeout_seconds == 300

class TestTavilyConfig:
    """Test Tavily configuration"""
    
    def test_default_config(self):
        config = TavilyConfig()
        assert config.max_results == 3
        assert config.max_queries == 3
        assert config.timeout_seconds == 20
    
    @patch.dict(os.environ, {"TAVILY_API_KEY": "tavily_test_key"})
    def test_api_key_from_env(self):
        config = TavilyConfig()
        assert config.api_key == "tavily_test_key"

class TestBusinessConfig:
    """Test business configuration"""
    
    def test_default_config(self):
        config = BusinessConfig()
        assert "IA" in config.product_service_context
        assert config.target_roi_increase == 5.27
        assert config.min_relevance_score == 0.7
        assert config.min_qualification_score == 0.6
        assert config.brazilian_market_focus == True

class TestNelliaProspectorConfig:
    """Test main configuration class"""
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    def test_default_initialization(self):
        config = NelliaProspectorConfig()
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.processing, ProcessingConfig)
        assert isinstance(config.tavily, TavilyConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.export, ExportConfig)
        assert isinstance(config.business, BusinessConfig)
        assert config.debug_mode == False
        assert config.development_mode == False
        assert config.metrics_enabled == True
    
    @patch.dict(os.environ, {
        "GEMINI_API_KEY": "test_key",
        "LLM_PROVIDER": "openai",
        "LLM_TEMPERATURE": "0.9",
        "MAX_LEADS_PER_BATCH": "50",
        "DEBUG_MODE": "true"
    })
    def test_environment_override(self):
        config = NelliaProspectorConfig()
        assert config.llm.provider == "openai"
        assert config.llm.temperature == 0.9
        assert config.processing.max_leads_per_batch == 50
        assert config.debug_mode == True
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    def test_validation_valid_config(self):
        # Should not raise any exception
        config = NelliaProspectorConfig()
        assert config is not None
    
    @patch.dict(os.environ, {
        "GEMINI_API_KEY": "test_key",
        "LLM_PROVIDER": "invalid_provider"
    })
    def test_validation_invalid_provider(self):
        with pytest.raises(ValueError, match="Invalid LLM provider"):
            NelliaProspectorConfig()
    
    @patch.dict(os.environ, {
        "GEMINI_API_KEY": "test_key",
        "LLM_TEMPERATURE": "3.0"
    })
    def test_validation_invalid_temperature(self):
        with pytest.raises(ValueError, match="temperature must be between"):
            NelliaProspectorConfig()
    
    @patch.dict(os.environ, {
        "GEMINI_API_KEY": "test_key",
        "MAX_LEADS_PER_BATCH": "-1"
    })
    def test_validation_invalid_batch_size(self):
        with pytest.raises(ValueError, match="must be positive"):
            NelliaProspectorConfig()
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    def test_get_agent_config(self):
        config = NelliaProspectorConfig()
        
        # Test base config
        agent_config = config.get_agent_config("unknown_agent")
        assert "llm_provider" in agent_config
        assert "llm_model" in agent_config
        assert "temperature" in agent_config
        assert "max_tokens" in agent_config
        assert "product_service_context" in agent_config
        assert "debug_mode" in agent_config
        
        # Test lead_intake specific config
        intake_config = config.get_agent_config("lead_intake")
        assert "skip_failed_extractions" in intake_config
        assert "max_text_length" in intake_config
        
        # Test enhanced_processor specific config
        processor_config = config.get_agent_config("enhanced_processor")
        assert "tavily_api_key" in processor_config
        assert "competitors_list" in processor_config
        assert "enable_tavily" in processor_config
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    def test_to_dict(self):
        config = NelliaProspectorConfig()
        config_dict = config.to_dict()
        
        assert "llm" in config_dict
        assert "processing" in config_dict
        assert "business" in config_dict
        assert "runtime" in config_dict
        
        assert config_dict["llm"]["provider"] == "gemini"
        assert config_dict["processing"]["max_leads_per_batch"] == 100
        assert config_dict["runtime"]["debug_mode"] == False

class TestGlobalConfiguration:
    """Test global configuration functions"""
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    def test_get_config_singleton(self):
        # Clear any existing instance
        import config
        config._config_instance = None
        
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2  # Should be the same instance
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    def test_reload_config(self):
        # Clear any existing instance
        import config
        config._config_instance = None
        
        config1 = get_config()
        config2 = reload_config()
        assert config1 is not config2  # Should be different instances

class TestConfigurationHelpers:
    """Test helper functions"""
    
    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    def test_helper_functions(self):
        from config import (
            is_debug_mode, is_development_mode, get_llm_config,
            get_processing_config, get_business_config
        )
        
        # Clear any existing instance
        import config
        config._config_instance = None
        
        assert is_debug_mode() == False
        assert is_development_mode() == False
        assert isinstance(get_llm_config(), LLMConfig)
        assert isinstance(get_processing_config(), ProcessingConfig)
        assert isinstance(get_business_config(), BusinessConfig)
    
    @patch.dict(os.environ, {
        "GEMINI_API_KEY": "test_key",
        "DEBUG_MODE": "true",
        "DEVELOPMENT_MODE": "true"
    })
    def test_helper_functions_enabled(self):
        from config import is_debug_mode, is_development_mode
        
        # Clear and reload config
        import config
        config._config_instance = None
        
        assert is_debug_mode() == True
        assert is_development_mode() == True

if __name__ == "__main__":
    pytest.main([__file__])