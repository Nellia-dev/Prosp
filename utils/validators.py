"""
Data validation utilities for Nellia Prospector
Provides validation functions for various data types and business rules.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse
from loguru import logger


class DataValidator:
    """Provides data validation utilities"""
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL format and accessibility
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url or not isinstance(url, str):
            return False, "URL must be a non-empty string"
        
        # Basic URL format validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            return False, "Invalid URL format"
        
        # Parse URL to check components
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                return False, "URL missing domain"
            if parsed.scheme not in ['http', 'https']:
                return False, "URL must use HTTP or HTTPS"
        except Exception as e:
            return False, f"URL parsing error: {str(e)}"
        
        return True, None
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not email or not isinstance(email, str):
            return False, "Email must be a non-empty string"
        
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        
        if not email_pattern.match(email):
            return False, "Invalid email format"
        
        return True, None
    
    @staticmethod
    def validate_text_content(text: str, min_length: int = 10, max_length: int = 50000) -> Tuple[bool, Optional[str]]:
        """
        Validate text content length and quality
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text or not isinstance(text, str):
            return False, "Text must be a non-empty string"
        
        # Check length
        text_length = len(text.strip())
        if text_length < min_length:
            return False, f"Text too short (minimum {min_length} characters)"
        
        if text_length > max_length:
            return False, f"Text too long (maximum {max_length} characters)"
        
        # Check for meaningful content (not just whitespace or repeated characters)
        cleaned_text = re.sub(r'\s+', ' ', text.strip())
        if len(set(cleaned_text)) < 10:  # Too few unique characters
            return False, "Text appears to be low quality (too few unique characters)"
        
        return True, None
    
    @staticmethod
    def validate_extraction_status(status: str) -> Tuple[bool, Optional[str]]:
        """
        Validate extraction status message
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not status or not isinstance(status, str):
            return False, "Status must be a non-empty string"
        
        valid_statuses = [
            "SUCESSO NA EXTRAÇÃO",
            "SUCESSO NA EXTRAÇÃO (VIA ANÁLISE DE IMAGEM)",
            "FALHA NA EXTRAÇÃO"
        ]
        
        # Check if status starts with valid prefix
        is_valid = any(status.startswith(valid_status) for valid_status in valid_statuses)
        
        if not is_valid:
            return False, f"Invalid extraction status: {status}"
        
        return True, None
    
    @staticmethod
    def validate_score(score: float, min_val: float = 0.0, max_val: float = 1.0) -> Tuple[bool, Optional[str]]:
        """
        Validate score value within range
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(score, (int, float)):
            return False, "Score must be a number"
        
        if score < min_val or score > max_val:
            return False, f"Score must be between {min_val} and {max_val}"
        
        return True, None
    
    @staticmethod
    def validate_list_not_empty(items: List[Any], field_name: str = "List") -> Tuple[bool, Optional[str]]:
        """
        Validate that list is not empty
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(items, list):
            return False, f"{field_name} must be a list"
        
        if not items:
            return False, f"{field_name} cannot be empty"
        
        return True, None
    
    @staticmethod
    def validate_dict_has_keys(data: Dict[str, Any], required_keys: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate that dictionary has required keys
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            return False, f"Missing required keys: {', '.join(missing_keys)}"
        
        return True, None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename for safe file system usage
        """
        if not filename:
            return "unnamed"
        
        # Remove/replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Trim and limit length
        sanitized = sanitized.strip('_')[:100]
        
        if not sanitized:
            return "unnamed"
        
        return sanitized
    
    @staticmethod
    def validate_harvester_output(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate harvester output structure
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required top-level keys
        required_keys = ["original_query", "collection_timestamp", "sites_data"]
        is_valid, error = DataValidator.validate_dict_has_keys(data, required_keys)
        if not is_valid:
            errors.append(error)
            return False, errors
        
        # Validate sites_data structure
        sites_data = data.get("sites_data", [])
        if not isinstance(sites_data, list):
            errors.append("sites_data must be a list")
            return False, errors
        
        # Validate individual site entries
        for i, site in enumerate(sites_data):
            if not isinstance(site, dict):
                errors.append(f"Site {i} must be a dictionary")
                continue
            
            # Check required site keys
            site_required_keys = ["url", "extracted_text_content", "extraction_status_message"]
            is_valid, error = DataValidator.validate_dict_has_keys(site, site_required_keys)
            if not is_valid:
                errors.append(f"Site {i}: {error}")
            
            # Validate URL
            url = site.get("url", "")
            is_valid, error = DataValidator.validate_url(url)
            if not is_valid:
                errors.append(f"Site {i}: URL validation failed - {error}")
            
            # Validate extraction status
            status = site.get("extraction_status_message", "")
            is_valid, error = DataValidator.validate_extraction_status(status)
            if not is_valid:
                errors.append(f"Site {i}: {error}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_business_rules(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate business-specific rules
        
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []
        
        # Check for reasonable data volumes
        if isinstance(data.get("sites_data"), list):
            site_count = len(data["sites_data"])
            if site_count > 1000:
                warnings.append(f"Large number of sites ({site_count}) may impact processing time")
            elif site_count == 0:
                warnings.append("No sites data found")
        
        # Check for extraction success rate
        if isinstance(data.get("sites_data"), list):
            successful_extractions = sum(
                1 for site in data["sites_data"] 
                if isinstance(site, dict) and 
                site.get("extraction_status_message", "").startswith("SUCESSO")
            )
            total_sites = len(data["sites_data"])
            
            if total_sites > 0:
                success_rate = successful_extractions / total_sites
                if success_rate < 0.5:
                    warnings.append(f"Low extraction success rate: {success_rate:.1%}")
        
        return True, warnings
