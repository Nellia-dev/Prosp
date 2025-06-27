"""
Lead Intake & Validation Agent - Validates and prepares lead data for processing.
"""
import asyncio
import re
import time
import traceback
from typing import Optional
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
            llm_client: An optional LLM client (not used by this agent).
            skip_failed_extractions: Whether to mark failed extractions as invalid
            **kwargs: Additional arguments for BaseAgent
        """
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.skip_failed_extractions = skip_failed_extractions

    async def process(self, lead_id: str, job_id: str, input_data: SiteData) -> ValidatedLead:
        """
        Process and validate lead data asynchronously.

        Args:
            lead_id: The ID of the lead.
            job_id: The ID of the job.
            input_data: Raw site data from harvester

        Returns:
            ValidatedLead object with validation results
        """
        start_time = time.time()
        await self._emit_event("agent_start", {
            "agent_name": self.name,
            "job_id": job_id,
            "lead_id": lead_id,
            "agent_description": self.description,
            "input_data": input_data.model_dump()
        })
        logger.info(f"Validating lead {lead_id}: {input_data.url}")

        try:
            validation_errors = []
            is_valid = True

            if not input_data.url:
                validation_errors.append("URL is missing")
                is_valid = False

            extraction_status = self._determine_extraction_status(input_data.extraction_status_message)

            if extraction_status in [ExtractionStatus.SUCCESS, ExtractionStatus.SUCCESS_VIA_IMAGE]:
                extraction_successful = True
            else:
                extraction_successful = False
                if self.skip_failed_extractions:
                    validation_errors.append(f"Extraction failed: {input_data.extraction_status_message}")
                    is_valid = False

            if extraction_successful:
                if not input_data.extracted_text_content or len(input_data.extracted_text_content.strip()) < 10:
                    validation_errors.append("Extracted text content is empty or too short")
                    is_valid = False

            cleaned_text = self._clean_text_content(input_data.extracted_text_content) if input_data.extracted_text_content else None

            if extraction_successful and cleaned_text and len(cleaned_text) < 50:
                validation_errors.append("Cleaned text content is too short (less than 50 characters)")

            if not input_data.google_search_data:
                validation_errors.append("Google search data is missing")

            validated_lead = ValidatedLead(
                site_data=input_data,
                validation_timestamp=datetime.now(),
                is_valid=is_valid,
                validation_errors=validation_errors,
                cleaned_text_content=cleaned_text,
                extraction_successful=extraction_successful
            )

            if is_valid:
                logger.info(f"Lead validated successfully: {input_data.url}")
            else:
                logger.warning(f"Lead validation failed: {input_data.url}, errors: {validation_errors}")

            duration = time.time() - start_time
            await self._emit_event("agent_end", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "duration": duration,
                "output": validated_lead.model_dump(exclude_none=True)
            })

            return validated_lead

        except Exception as e:
            duration = time.time() - start_time
            error_message = f"An unexpected error occurred in {self.name}: {e}"
            logger.error(error_message, exc_info=True)
            await self._emit_event("pipeline_error", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "duration": duration,
                "error_message": str(e),
                "details": traceback.format_exc()
            })
            raise

    def _determine_extraction_status(self, status_message: Optional[str]) -> ExtractionStatus:
        if not status_message:
            return ExtractionStatus.FAILED_OTHER
        status_lower = status_message.lower()

        if "sucesso" in status_lower:
            return ExtractionStatus.SUCCESS_VIA_IMAGE if "análise de imagem" in status_lower else ExtractionStatus.SUCCESS
        elif "timeout" in status_lower:
            return ExtractionStatus.FAILED_TIMEOUT
        elif "status" in status_lower and "retornou" in status_lower:
            return ExtractionStatus.FAILED_STATUS
        else:
            return ExtractionStatus.FAILED_OTHER

    def _clean_text_content(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'TEXTO DO DOM \(PARCIAL\):', '', text)
        text = re.sub(r'ANÁLISE COMPLEMENTAR DA IMAGEM PELA IA:', '\n\nANÁLISE DA IMAGEM:', text)
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        text = re.sub(r'([.!?]){2,}', r'\1', text)

        max_length = 10000
        if len(text) > max_length:
            text = text[:max_length] + "... [texto truncado]"
        return text


if __name__ == '__main__':
    import sys

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    async def main():
        event_queue = asyncio.Queue()
        agent = LeadIntakeAgent(
            name="TestLeadIntakeAgent",
            description="Validates and cleans lead data.",
            event_queue=event_queue,
            user_id="test_user",
            skip_failed_extractions=True
        )

        logger.info("\n--- Running Test Case 1: Valid Lead ---")
        valid_site_data = SiteData(
            url="http://example.com",
            google_search_data={"title": "Example Domain"},
            extracted_text_content="This is some perfectly valid and sufficiently long extracted text content from the website.",
            extraction_status_message="Extração de texto via DOM realizada com sucesso."
        )
        validated_lead_1 = await agent.process("lead_valid_123", "job_valid_456", valid_site_data)
        logger.info(f"Validation result: is_valid={validated_lead_1.is_valid}, errors: {validated_lead_1.validation_errors}")
        assert validated_lead_1.is_valid is True
        assert not validated_lead_1.validation_errors

        logger.info("\n--- Running Test Case 2: Invalid Lead (Failed Extraction) ---")
        invalid_site_data = SiteData(
            url="http://fail.com",
            google_search_data={"title": "Fail Domain"},
            extracted_text_content="",
            extraction_status_message="Extração falhou: Timeout"
        )
        validated_lead_2 = await agent.process("lead_invalid_789", "job_invalid_101", invalid_site_data)
        logger.info(f"Validation result: is_valid={validated_lead_2.is_valid}, errors: {validated_lead_2.validation_errors}")
        assert validated_lead_2.is_valid is False
        assert "Extraction failed" in validated_lead_2.validation_errors[0]

        logger.info("\n--- Verifying Emitted Events ---")
        event_count = 0
        while not event_queue.empty():
            event = await event_queue.get()
            logger.info(f"Event received: {event['event_type']} for lead {event['payload']['lead_id']}")
            event_count += 1
        assert event_count == 4
        logger.info("✅ Event verification successful.")

        logger.info("\n✅ All test cases for LeadIntakeAgent passed.")

    asyncio.run(main()) 