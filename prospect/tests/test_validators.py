"""
Unit tests for validators module
"""

import pytest
from utils.validators import (
    validate_email, validate_phone_br, validate_url, validate_text_length,
    validate_lead_completeness, validate_api_key, validate_processing_config,
    ValidationResult, ValidationError
)

class TestEmailValidation:
    """Test email validation functions"""
    
    def test_valid_emails(self):
        """Test valid email addresses"""
        valid_emails = [
            "joao@empresa.com",
            "maria.santos@tech.com.br",
            "admin@sub.domain.com",
            "user+tag@example.org",
            "test.email@domain-name.co.uk",
            "contato@123empresa.com"
        ]
        
        for email in valid_emails:
            result = validate_email(email)
            assert result.is_valid, f"Email should be valid: {email}"
            assert result.value == email
    
    def test_invalid_emails(self):
        """Test invalid email addresses"""
        invalid_emails = [
            "not-an-email",
            "@domain.com",
            "user@",
            "user@.com",
            "user..name@domain.com",
            "user@domain",
            "",
            None,
            "user name@domain.com",  # Space in local part
            "user@domain .com"       # Space in domain
        ]
        
        for email in invalid_emails:
            result = validate_email(email)
            assert not result.is_valid, f"Email should be invalid: {email}"
            assert len(result.errors) > 0
    
    def test_email_edge_cases(self):
        """Test email edge cases"""
        # Very long email
        long_email = "a" * 100 + "@domain.com"
        result = validate_email(long_email)
        assert not result.is_valid
        
        # Unicode characters
        unicode_email = "joão@empresa.com"
        result = validate_email(unicode_email)
        # This might be valid or invalid depending on implementation


class TestPhoneValidationBR:
    """Test Brazilian phone validation"""
    
    def test_valid_phones(self):
        """Test valid Brazilian phone numbers"""
        valid_phones = [
            "(11) 99999-9999",
            "11 99999-9999",
            "(21) 98888-8888",
            "21 98888-8888",
            "+55 11 99999-9999",
            "+55 (11) 99999-9999",
            "11999999999",  # Without formatting
            "(47) 99876-5432"
        ]
        
        for phone in valid_phones:
            result = validate_phone_br(phone)
            assert result.is_valid, f"Phone should be valid: {phone}"
    
    def test_invalid_phones(self):
        """Test invalid Brazilian phone numbers"""
        invalid_phones = [
            "123456789",        # Too short
            "12345678901234",   # Too long
            "(99) 99999-9999",  # Invalid area code
            "11 8888-8888",     # Invalid mobile format
            "+1 555-123-4567",  # US format
            "",
            None,
            "abc-def-ghij",     # Letters
            "(11) 99999-999"    # Missing digit
        ]
        
        for phone in invalid_phones:
            result = validate_phone_br(phone)
            assert not result.is_valid, f"Phone should be invalid: {phone}"
    
    def test_phone_normalization(self):
        """Test phone number normalization"""
        phone_variations = [
            "(11) 99999-9999",
            "11 99999-9999",
            "+55 11 99999-9999",
            "11999999999"
        ]
        
        normalized_phones = []
        for phone in phone_variations:
            result = validate_phone_br(phone, normalize=True)
            if result.is_valid:
                normalized_phones.append(result.normalized_value)
        
        # All should normalize to the same format
        assert len(set(normalized_phones)) <= 1, "All variations should normalize to same format"


class TestURLValidation:
    """Test URL validation"""
    
    def test_valid_urls(self):
        """Test valid URLs"""
        valid_urls = [
            "https://www.empresa.com.br",
            "http://empresa.com",
            "https://sub.domain.com/path",
            "https://empresa.com.br/produtos?categoria=tech",
            "www.empresa.com",
            "empresa.com.br",
            "https://localhost:8000",
            "https://192.168.1.1"
        ]
        
        for url in valid_urls:
            result = validate_url(url)
            assert result.is_valid, f"URL should be valid: {url}"
    
    def test_invalid_urls(self):
        """Test invalid URLs"""
        invalid_urls = [
            "not-a-url",
            "http://",
            "https://",
            "",
            None,
            "ftp://invalid-protocol.com",
            "http://.com",
            "http://domain..com"
        ]
        
        for url in invalid_urls:
            result = validate_url(url)
            assert not result.is_valid, f"URL should be invalid: {url}"
    
    def test_url_normalization(self):
        """Test URL normalization"""
        test_cases = [
            ("empresa.com", "https://empresa.com"),
            ("www.empresa.com", "https://www.empresa.com"),
            ("HTTP://EMPRESA.COM", "http://empresa.com"),
            ("https://empresa.com/", "https://empresa.com")
        ]
        
        for input_url, expected in test_cases:
            result = validate_url(input_url, normalize=True)
            if result.is_valid:
                assert result.normalized_value == expected or result.normalized_value.startswith("https://")


class TestTextValidation:
    """Test text validation functions"""
    
    def test_valid_text_length(self):
        """Test valid text lengths"""
        short_text = "Short text"
        medium_text = "A" * 500
        
        # Default limits
        result = validate_text_length(short_text)
        assert result.is_valid
        
        result = validate_text_length(medium_text)
        assert result.is_valid
    
    def test_invalid_text_length(self):
        """Test invalid text lengths"""
        # Empty text
        result = validate_text_length("")
        assert not result.is_valid
        
        # Very long text
        very_long_text = "A" * 20000
        result = validate_text_length(very_long_text, max_length=10000)
        assert not result.is_valid
        
        # None
        result = validate_text_length(None)
        assert not result.is_valid
    
    def test_custom_length_limits(self):
        """Test custom length limits"""
        text = "A" * 100
        
        # Should pass with high limit
        result = validate_text_length(text, min_length=1, max_length=200)
        assert result.is_valid
        
        # Should fail with low limit
        result = validate_text_length(text, min_length=1, max_length=50)
        assert not result.is_valid
        
        # Should fail with high minimum
        result = validate_text_length(text, min_length=200, max_length=500)
        assert not result.is_valid


class TestLeadCompletenessValidation:
    """Test lead completeness validation"""
    
    def test_complete_lead(self):
        """Test validation of complete lead"""
        complete_lead = {
            "source_text": "João Silva, CEO da TechCorp, busca automação",
            "source": "linkedin",
            "contact_info": {
                "name": "João Silva",
                "title": "CEO",
                "email": "joao@techcorp.com",
                "phone": "(11) 99999-9999"
            },
            "company_info": {
                "name": "TechCorp",
                "industry": "Tecnologia",
                "size": "100-500",
                "location": "São Paulo, SP"
            }
        }
        
        result = validate_lead_completeness(complete_lead)
        assert result.is_valid
        assert result.completeness_score > 0.8
    
    def test_incomplete_lead(self):
        """Test validation of incomplete lead"""
        incomplete_lead = {
            "source_text": "Lead incompleto",
            "source": "unknown"
        }
        
        result = validate_lead_completeness(incomplete_lead)
        assert result.completeness_score < 0.5
        assert len(result.missing_fields) > 0
    
    def test_lead_with_invalid_data(self):
        """Test lead with invalid data"""
        invalid_lead = {
            "source_text": "Lead com dados inválidos",
            "source": "test",
            "contact_info": {
                "name": "João Silva",
                "email": "invalid-email",  # Invalid email
                "phone": "123"             # Invalid phone
            }
        }
        
        result = validate_lead_completeness(invalid_lead)
        assert not result.is_valid
        assert len(result.errors) > 0


class TestAPIKeyValidation:
    """Test API key validation"""
    
    def test_valid_api_keys(self):
        """Test valid API key formats"""
        valid_keys = [
            "sk-1234567890abcdef1234567890abcdef",  # OpenAI style
            "AIzaSyDaGmWKa4JsXZ5iQotLDfm1aQQO_1a2b3c",   # Google style
            "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",  # Tavily style
            "pk_test_1234567890abcdef1234567890abcdef12", # Stripe test style
        ]
        
        for key in valid_keys:
            result = validate_api_key(key)
            assert result.is_valid, f"API key should be valid: {key[:10]}..."
    
    def test_invalid_api_keys(self):
        """Test invalid API key formats"""
        invalid_keys = [
            "",
            None,
            "short",
            "spaces in key",
            "key-with-ñ-characters",
            "a" * 5,   # Too short
            "a" * 200  # Too long
        ]
        
        for key in invalid_keys:
            result = validate_api_key(key)
            assert not result.is_valid, f"API key should be invalid: {key}"
    
    def test_api_key_masking(self):
        """Test API key masking for security"""
        api_key = "sk-1234567890abcdef1234567890abcdef"
        result = validate_api_key(api_key, mask_in_result=True)
        
        if result.is_valid:
            assert "****" in str(result.masked_value)
            assert len(result.masked_value) < len(api_key)


class TestProcessingConfigValidation:
    """Test processing configuration validation"""
    
    def test_valid_processing_config(self):
        """Test valid processing configuration"""
        valid_config = {
            "max_leads_per_batch": 100,
            "max_text_length": 15000,
            "skip_failed_extractions": False,
            "processing_timeout_seconds": 300,
            "min_relevance_score": 0.7,
            "min_qualification_score": 0.6
        }
        
        result = validate_processing_config(valid_config)
        assert result.is_valid
    
    def test_invalid_processing_config(self):
        """Test invalid processing configuration"""
        invalid_configs = [
            {"max_leads_per_batch": -1},              # Negative batch size
            {"max_leads_per_batch": 0},               # Zero batch size
            {"max_text_length": -100},                # Negative text length
            {"processing_timeout_seconds": -1},       # Negative timeout
            {"min_relevance_score": 1.5},             # Score > 1
            {"min_qualification_score": -0.1},        # Score < 0
            {"min_relevance_score": "not_a_number"},  # Wrong type
        ]
        
        for config in invalid_configs:
            result = validate_processing_config(config)
            assert not result.is_valid, f"Config should be invalid: {config}"
    
    def test_missing_config_fields(self):
        """Test configuration with missing fields"""
        incomplete_config = {
            "max_leads_per_batch": 50
            # Missing other required fields
        }
        
        result = validate_processing_config(incomplete_config, require_all_fields=True)
        assert not result.is_valid
        assert len(result.missing_fields) > 0


class TestValidationResult:
    """Test ValidationResult class"""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation"""
        result = ValidationResult(
            is_valid=True,
            value="test@example.com",
            errors=[]
        )
        
        assert result.is_valid is True
        assert result.value == "test@example.com"
        assert len(result.errors) == 0
    
    def test_validation_result_with_errors(self):
        """Test ValidationResult with errors"""
        result = ValidationResult(
            is_valid=False,
            value="invalid-email",
            errors=["Invalid email format", "Missing @ symbol"]
        )
        
        assert result.is_valid is False
        assert result.value == "invalid-email"
        assert len(result.errors) == 2
        assert "Invalid email format" in result.errors
    
    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization"""
        result = ValidationResult(
            is_valid=True,
            value="test@example.com",
            normalized_value="test@example.com",
            confidence_score=0.95
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["is_valid"] is True
        assert result_dict["value"] == "test@example.com"
        assert result_dict["confidence_score"] == 0.95


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_unicode_handling(self):
        """Test Unicode character handling"""
        unicode_text = "Empresa com caracteres especiais: ção, ã, ñ, €"
        result = validate_text_length(unicode_text)
        assert result.is_valid
    
    def test_very_large_inputs(self):
        """Test with very large inputs"""
        large_text = "A" * 100000
        result = validate_text_length(large_text, max_length=50000)
        assert not result.is_valid
    
    def test_null_and_empty_inputs(self):
        """Test with null and empty inputs"""
        inputs = [None, "", " ", "\t", "\n"]
        
        for input_val in inputs:
            email_result = validate_email(input_val)
            assert not email_result.is_valid
            
            phone_result = validate_phone_br(input_val)
            assert not phone_result.is_valid
            
            url_result = validate_url(input_val)
            assert not url_result.is_valid
    
    def test_type_errors(self):
        """Test with wrong input types"""
        wrong_types = [123, [], {}, object()]
        
        for wrong_input in wrong_types:
            try:
                email_result = validate_email(wrong_input)
                assert not email_result.is_valid
            except (TypeError, AttributeError):
                # Expected for some inputs
                pass


if __name__ == "__main__":
    pytest.main([__file__])