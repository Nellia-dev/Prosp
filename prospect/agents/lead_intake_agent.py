"""
Lead Intake & Validation Agent - Validates and prepares lead data for processing.
"""

import re
from typing import List, Optional
from loguru import logger
from datetime import datetime

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase
from data_models.lead_structures import (
    SiteData,
    ValidatedLead,
    ExtractionStatus
)


class LeadIntakeAgent(BaseAgent[SiteData, ValidatedLead]):
    """
    Agent responsible for:
    - Validating lead data structure
    - Filtering out invalid or failed extractions
    - Cleaning and normalizing text content
    - Preparing leads for analysis
    """
    
    def __init__(self, name: str, description: str, llm_client: Optional[LLMClientBase] = None, skip_failed_extractions: bool = False, **kwargs):
        """
        Initialize the Lead Intake Agent.
        
        Args:
            name: The name of the agent.
            description: A description of the agent.
            llm_client: An optional LLM client.
            skip_failed_extractions: Whether to mark failed extractions as invalid
            **kwargs: Additional arguments for BaseAgent
        """
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.skip_failed_extractions = skip_failed_extractions
    
    def process(self, input_data: SiteData) -> ValidatedLead:
        """
        Process and validate lead data.
        
        Args:
            input_data: Raw site data from harvester
            
        Returns:
            ValidatedLead object with validation results
        """
        logger.info(f"Validating lead: {input_data.url}")
        
        validation_errors = []
        is_valid = True
        extraction_successful = False
        
        # Check URL validity
        if not input_data.url:
            validation_errors.append("URL is missing")
            is_valid = False
        
        # Check extraction status
        extraction_status = self._determine_extraction_status(input_data.extraction_status_message)
        
        if extraction_status in [ExtractionStatus.SUCCESS, ExtractionStatus.SUCCESS_VIA_IMAGE]:
            extraction_successful = True
        else:
            extraction_successful = False
            if self.skip_failed_extractions:
                validation_errors.append(f"Extraction failed: {input_data.extraction_status_message}")
                is_valid = False
        
        # Validate extracted content
        if extraction_successful:
            if not input_data.extracted_text_content or len(input_data.extracted_text_content.strip()) < 10:
                validation_errors.append("Extracted text content is empty or too short")
                is_valid = False
        
        # Clean text content if available
        cleaned_text = None
        if input_data.extracted_text_content:
            cleaned_text = self._clean_text_content(input_data.extracted_text_content)
            
            # Additional validation on cleaned content
            if extraction_successful and len(cleaned_text) < 50:
                validation_errors.append("Cleaned text content is too short (less than 50 characters)")
                # Don't mark as invalid, just note the issue
        
        # Check Google search data
        if not input_data.google_search_data:
            validation_errors.append("Google search data is missing")
            # This is not critical, so don't mark as invalid
        
        # Create validated lead
        validated_lead = ValidatedLead(
            site_data=input_data,
            validation_timestamp=datetime.now(),
            is_valid=is_valid,
            validation_errors=validation_errors,
            cleaned_text_content=cleaned_text,
            extraction_successful=extraction_successful
        )
        
        # Log validation results
        if is_valid:
            logger.info(f"Lead validated successfully: {input_data.url}")
        else:
            logger.warning(f"Lead validation failed: {input_data.url}, errors: {validation_errors}")
        
        return validated_lead
    
    def _determine_extraction_status(self, status_message: str) -> ExtractionStatus:
        """Determine the extraction status from the status message"""
        status_lower = status_message.lower()
        
        if "sucesso" in status_lower:
            if "análise de imagem" in status_lower:
                return ExtractionStatus.SUCCESS_VIA_IMAGE
            return ExtractionStatus.SUCCESS
        elif "timeout" in status_lower:
            return ExtractionStatus.FAILED_TIMEOUT
        elif "status" in status_lower and "retornou" in status_lower:
            return ExtractionStatus.FAILED_STATUS
        else:
            return ExtractionStatus.FAILED_OTHER
    
    def _clean_text_content(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text content
            
        Returns:
            Cleaned text content
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove common extraction artifacts
        text = re.sub(r'TEXTO DO DOM \(PARCIAL\):', '', text)
        text = re.sub(r'ANÁLISE COMPLEMENTAR DA IMAGEM PELA IA:', '\n\nANÁLISE DA IMAGEM:', text)
        
        # Remove HTML entities
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        
        # Remove URLs (optional, depending on use case)
        # text = re.sub(r'https?://\S+', '[URL]', text)
        
        # Remove repeated punctuation
        text = re.sub(r'([.!?]){2,}', r'\1', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Limit text length to avoid overwhelming downstream agents
        max_length = 10000  # characters
        if len(text) > max_length:
            text = text[:max_length] + "... [texto truncado]"
        
        return text
    
    def validate_batch(self, site_data_list: List[SiteData]) -> List[ValidatedLead]:
        """
        Validate a batch of leads.
        
        Args:
            site_data_list: List of site data to validate
            
        Returns:
            List of validated leads
        """
        validated_leads = []
        
        for site_data in site_data_list:
            try:
                validated_lead = self.execute(site_data)
                validated_leads.append(validated_lead)
            except Exception as e:
                logger.error(f"Error validating lead {site_data.url}: {e}")
                # Create a failed validation entry
                validated_lead = ValidatedLead(
                    site_data=site_data,
                    validation_timestamp=datetime.now(),
                    is_valid=False,
                    validation_errors=[f"Validation process failed: {str(e)}"],
                    cleaned_text_content=None,
                    extraction_successful=False
                )
                validated_leads.append(validated_lead)
        
        # Summary statistics
        valid_count = sum(1 for lead in validated_leads if lead.is_valid)
        total_count = len(validated_leads)
        
        logger.info(
            f"Batch validation complete: {valid_count}/{total_count} leads are valid "
            f"({valid_count/total_count*100:.1f}%)"
        )
        
        return validated_leads
    
    def get_validation_summary(self, validated_leads: List[ValidatedLead]) -> dict:
        """
        Get a summary of validation results.
        
        Args:
            validated_leads: List of validated leads
            
        Returns:
            Dictionary with validation statistics
        """
        total = len(validated_leads)
        valid = sum(1 for lead in validated_leads if lead.is_valid)
        extraction_successful = sum(1 for lead in validated_leads if lead.extraction_successful)
        
        # Count validation errors
        error_counts = {}
        for lead in validated_leads:
            for error in lead.validation_errors:
                error_type = error.split(':')[0]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return {
            "total_leads": total,
            "valid_leads": valid,
            "invalid_leads": total - valid,
            "validation_rate": valid / total if total > 0 else 0,
            "extraction_successful": extraction_successful,
            "extraction_failed": total - extraction_successful,
            "common_errors": error_counts,
            "timestamp": datetime.now().isoformat()
        } 