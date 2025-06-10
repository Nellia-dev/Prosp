# prospect/pipeline_orchestrator.py

import asyncio
import traceback
import os
import time
from typing import Dict, Any, AsyncIterator
from datetime import datetime
import uuid

from loguru import logger

# Event Models
from event_models import (
    PipelineStartEvent,
    PipelineEndEvent,
    AgentStartEvent,
    AgentEndEvent,
    LeadGeneratedEvent,
    StatusUpdateEvent,
    PipelineErrorEvent,
    LeadEnrichmentStartEvent,
    LeadEnrichmentEndEvent,
)

# ADK Agents (Harvester)
from adk1.agent import (
    root_agent as harvester_query_refiner_agent,
    lead_search_and_qualify_agent as harvester_search_agent,
)

# Enhanced Processor Agents
from agents.lead_intake_agent import LeadIntakeAgent
from agents.lead_analysis_agent import LeadAnalysisAgent
from agents.enhanced_lead_processor import EnhancedLeadProcessor
from data_models.lead_structures import SiteData, GoogleSearchData
from core_logic.llm_client import LLMClientFactory

# ADK Runner
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Constants
ADK_APP_NAME = "prospecter_harvester"
ADK_USER_ID = "prospector_user_1"
ADK_SESSION_SERVICE = InMemorySessionService()


class PipelineOrchestrator:
    """
    Orchestrates the entire lead generation and enrichment pipeline,
    from initial harvesting to deep enrichment, yielding real-time events.
    """

    def __init__(self, business_context: Dict[str, Any], user_id: str, job_id: str):
        self.business_context = business_context
        self.user_id = user_id
        self.job_id = job_id
        self.product_service_context = business_context.get("product_service_description", "")
        self.competitors_list = ", ".join(business_context.get("competitors", []))
        
        # Initialize a single LLM client to be shared by all agents
        self.llm_client = LLMClientFactory.create_from_env()
        
        # Initialize the Enhanced Processor agents here
        self.lead_intake_agent = LeadIntakeAgent(
            llm_client=self.llm_client,
            name="LeadIntakeAgent",
            description="Validates and prepares lead data for processing."
        )
        self.lead_analysis_agent = LeadAnalysisAgent(
            llm_client=self.llm_client,
            name="LeadAnalysisAgent",
            description="Analyzes validated lead data to extract key business insights.",
            product_service_context=self.product_service_context
        )
        self.enhanced_lead_processor = EnhancedLeadProcessor(
            llm_client=self.llm_client,
            name="EnhancedLeadProcessor",
            description="Orchestrates a series of specialized agents to generate a rich, multi-faceted prospect package.",
            product_service_context=self.product_service_context,
            competitors_list=self.competitors_list,
            tavily_api_key=os.getenv("TAVILY_API_KEY")
        )
        logger.info(f"PipelineOrchestrator initialized for job {self.job_id}")

    def _generate_search_query_directly(self, business_desc: str, target_market: str, industry_focus) -> str:
        """
        Generate search query directly from business context without using the ADK agent.
        This is a fallback mechanism when the agent fails to work properly.
        """
        keywords = []
        
        # Process business description
        if business_desc:
            # Extract meaningful keywords from business description
            words = business_desc.lower().replace(",", " ").split()
            
            # Map Portuguese business terms to search keywords
            business_term_mapping = {
                "consultoria": "consulting",
                "consultor": "consultant",
                "inteligencia": "intelligence",
                "artificial": "artificial",
                "especializada": "specialized",
                "especializado": "specialized",
                "tecnologia": "technology",
                "automacao": "automation",
                "transformacao": "transformation",
                "digital": "digital",
                "software": "software",
                "sistema": "system",
                "solucao": "solution"
            }
            
            # Extract and translate key business terms
            for word in words:
                clean_word = word.strip().lower()
                if len(clean_word) > 3:
                    if clean_word in business_term_mapping:
                        keywords.append(business_term_mapping[clean_word])
                    elif clean_word not in ['para', 'com', 'uma', 'das', 'the', 'and', 'for', 'with', 'que', 'este', 'esta', 'essa', 'isso']:
                        keywords.append(clean_word)
        
        # Process target market
        if target_market:
            if any(x in target_market.lower() for x in ["brazil", "brasil"]):
                keywords.append("Brazil")
            if "sao paulo" in target_market.lower() or "são paulo" in target_market.lower():
                keywords.append("São Paulo")
        
        # Process industry focus
        if industry_focus:
            industry_mapping = {
                "pequenas": "small",
                "media": "medium",
                "medias": "medium",
                "empresas": "companies",
                "company": "companies",
                "empresa": "company"
            }
            
            if isinstance(industry_focus, list):
                for industry in industry_focus:
                    industry_words = str(industry).lower().split()
                    for word in industry_words:
                        if word in industry_mapping:
                            keywords.append(industry_mapping[word])
                        elif len(word) > 3:
                            keywords.append(word)
            else:
                industry_words = str(industry_focus).lower().split()
                for word in industry_words:
                    if word in industry_mapping:
                        keywords.append(industry_mapping[word])
                    elif len(word) > 3:
                        keywords.append(word)
        
        # Ensure we have at least some default keywords
        if not keywords:
            keywords = ["small", "medium", "companies", "Brazil", "business"]
        
        # Remove duplicates while preserving order
        unique_keywords = []
        for keyword in keywords:
            if keyword not in unique_keywords:
                unique_keywords.append(keyword)
        
        return " ".join(unique_keywords[:8])  # Limit to 8 keywords for better search results

    async def execute_streaming_pipeline(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Main entry point to run the unified pipeline.
        It harvests leads and concurrently enriches them.
        """
        start_time = time.time()
        yield PipelineStartEvent(
            event_type="pipeline_start",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            initial_query=self.business_context.get("business_description", "N/A"),
            max_leads_to_generate=self.business_context.get("max_leads_to_generate", 10)
        ).to_dict()

        enrichment_tasks = []
        leads_found = 0
        try:
            # Start the harvester as the main task
            async for raw_lead_data in self._run_harvester():
                
                # Skip example.com or invalid leads
                website_url = raw_lead_data.get("website", "")
                if "example.com" in website_url or not website_url or website_url == "N/A":
                    logger.warning(f"[{self.job_id}] Skipping invalid lead: {website_url}")
                    continue
                
                # For each lead found, yield the event and start enrichment
                lead_id = str(uuid.uuid4())
                leads_found += 1
                
                yield LeadGeneratedEvent(
                    event_type="lead_generated",
                    timestamp=datetime.now().isoformat(),
                    job_id=self.job_id,
                    user_id=self.user_id,
                    lead_id=lead_id,
                    lead_data=raw_lead_data,
                    source_url=raw_lead_data.get("website", "N/A"),
                    agent_name=harvester_search_agent.name
                ).to_dict()

                # Create a concurrent task for enriching this lead
                async def _run_enrichment_and_collect_events(lead_data, lead_id):
                    events = []
                    async for event in self._enrich_lead(lead_data, lead_id):
                        events.append(event)
                    return events

                task = asyncio.create_task(_run_enrichment_and_collect_events(raw_lead_data, lead_id))
                enrichment_tasks.append(task)
                await asyncio.sleep(5) # Add a delay to avoid rate limiting

            # Wait for all enrichment tasks to complete
            if leads_found == 0:
                yield StatusUpdateEvent(
                    event_type="status_update",
                    timestamp=datetime.now().isoformat(),
                    job_id=self.job_id,
                    user_id=self.user_id,
                    status_message="No valid leads were found by the harvester. Please check your business description and try refining your search criteria."
                ).to_dict()
            else:
                yield StatusUpdateEvent(
                    event_type="status_update",
                    timestamp=datetime.now().isoformat(),
                    job_id=self.job_id,
                    user_id=self.user_id,
                    status_message=f"Harvester finished. Found {leads_found} leads. Waiting for all enrichment tasks to complete..."
                ).to_dict()

            for task_future in asyncio.as_completed(enrichment_tasks):
                events = await task_future
                for event in events:
                    yield event

        except Exception as e:
            logger.error(f"Critical error in pipeline for job {self.job_id}: {e}")
            yield PipelineErrorEvent(
                event_type="pipeline_error",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                error_message=str(e),
                error_type=type(e).__name__
            ).to_dict()
        finally:
            total_time = time.time() - start_time
            yield PipelineEndEvent(
                event_type="pipeline_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                total_leads_generated=len(enrichment_tasks),
                execution_time_seconds=total_time,
                success=True # Assuming success if no critical error
            ).to_dict()

    async def _run_harvester(self) -> AsyncIterator[Dict[str, Any]]:
        """
        Runs the ADK-based harvester agent to find potential leads.
        """
        logger.info(f"[{self.job_id}] Starting harvester...")
        
        query_refiner_runner = Runner(
            app_name=ADK_APP_NAME,
            agent=harvester_query_refiner_agent,
            session_service=ADK_SESSION_SERVICE,
        )
        
        search_runner = Runner(
            app_name=ADK_APP_NAME,
            agent=harvester_search_agent,
            session_service=ADK_SESSION_SERVICE,
        )

        # Build a comprehensive search request from business context
        business_desc = self.business_context.get("business_description", "")
        target_market = self.business_context.get("target_market", "")
        industry_focus = self.business_context.get("industry_focus", [])
        location = self.business_context.get("location", "")
        
        if not business_desc:
            logger.warning("No business description found in context for harvester.")
            return

        # Create a comprehensive search request
        initial_query = f"Business: {business_desc}"
        if target_market:
            initial_query += f" Target market: {target_market}"
        if industry_focus:
            industries = ", ".join(industry_focus) if isinstance(industry_focus, list) else str(industry_focus)
            initial_query += f" Industries: {industries}"
        if location:
            initial_query += f" Location: {location}"
        
        initial_query += " - Find potential leads and customers for this business."
        
        logger.info(f"[{self.job_id}] Initial query for refiner: {initial_query}")

        try:
            session_id = str(uuid.uuid4())
            logger.debug(f"[{self.job_id}] Creating ADK session with ID: {session_id}")
            
            await ADK_SESSION_SERVICE.create_session(
                session_id=session_id, app_name=ADK_APP_NAME, user_id=self.user_id
            )
            logger.debug(f"[{self.job_id}] ADK session created successfully")
            
            # Verify agent configuration
            logger.debug(f"[{self.job_id}] Query refiner agent name: {harvester_query_refiner_agent.name}")
            logger.debug(f"[{self.job_id}] Query refiner agent model: {harvester_query_refiner_agent.model}")
            logger.debug(f"[{self.job_id}] Query refiner agent description: {harvester_query_refiner_agent.description}")
            logger.debug(f"[{self.job_id}] Query refiner agent instruction preview: {harvester_query_refiner_agent.instruction[:200]}...")
            
            refined_query_response = None
            # Refine the query
            query_content = types.Content(parts=[types.Part(text=initial_query)])
            logger.debug(f"[{self.job_id}] Sending to query refiner: '{initial_query}'")
            logger.debug(f"[{self.job_id}] Query content type: {type(query_content)}")
            logger.debug(f"[{self.job_id}] Query content parts: {len(query_content.parts)}")
            logger.debug(f"[{self.job_id}] Query content parts[0].text: '{query_content.parts[0].text}'")
            logger.debug(f"[{self.job_id}] Query content role: {query_content.role if hasattr(query_content, 'role') else 'No role'}")
            
            response_count = 0
            logger.info(f"[{self.job_id}] Starting ADK runner with user_id='{self.user_id}', session_id='{session_id}'")
            
            async for response in query_refiner_runner.run_async(
                user_id=self.user_id,
                session_id=session_id,
                new_message=query_content,
            ):
                response_count += 1
                logger.debug(f"[{self.job_id}] Query refiner response #{response_count}: {type(response)}")
                logger.debug(f"[{self.job_id}] Response full data: {response}")
                
                # Log additional response details
                if hasattr(response, 'author'):
                    logger.debug(f"[{self.job_id}] Response author: {response.author}")
                    
                # Check if this is actually our agent responding
                if hasattr(response, 'author') and response.author != 'query_refiner_agent':
                    logger.warning(f"[{self.job_id}] Response from unexpected agent: {response.author}")
                    
                if hasattr(response, 'content') and response.content:
                    logger.debug(f"[{self.job_id}] Response content parts count: {len(response.content.parts) if hasattr(response.content, 'parts') else 'No parts'}")
                    if hasattr(response.content, 'parts') and response.content.parts:
                        for i, part in enumerate(response.content.parts):
                            if hasattr(part, 'text'):
                                logger.debug(f"[{self.job_id}] Response part {i} text (raw): {repr(part.text)}")
                                logger.debug(f"[{self.job_id}] Response part {i} text (display): '{part.text}'")
                            else:
                                logger.debug(f"[{self.job_id}] Response part {i} has no text attribute")
                
                # Take the last non-empty response
                if response:
                    refined_query_response = response
            
            logger.info(f"[{self.job_id}] Query refiner returned {response_count} responses")
            
            if not refined_query_response:
                logger.warning(f"[{self.job_id}] Query refiner did not return any response, using fallback")
                search_query = self._generate_search_query_directly(business_desc, target_market, industry_focus)
                logger.info(f"[{self.job_id}] Using fallback query: {search_query}")
            else:
                # Extract text from Content object with proper cleanup
                logger.debug(f"[{self.job_id}] Raw refined_query_response: {type(refined_query_response)}")
                
                search_query = None
                if hasattr(refined_query_response, 'content'):
                    content = refined_query_response.content
                    logger.debug(f"[{self.job_id}] Content type: {type(content)}")
                    
                    if hasattr(content, 'parts') and content.parts:
                        logger.debug(f"[{self.job_id}] Content has {len(content.parts)} parts")
                        for i, part in enumerate(content.parts):
                            if hasattr(part, 'text') and part.text:
                                raw_text = part.text
                                # Clean up the text properly - remove newlines, whitespace, and common invalid responses
                                clean_text = raw_text.strip().replace('\n', ' ').replace('\r', ' ')
                                # Remove extra whitespace
                                clean_text = ' '.join(clean_text.split())
                                
                                logger.debug(f"[{self.job_id}] Raw text from part {i}: '{raw_text}'")
                                logger.debug(f"[{self.job_id}] Cleaned text from part {i}: '{clean_text}'")
                                
                                # Validate if this is a proper search query
                                invalid_responses = ["ok", "okay", "aguardando", "provide", "request", "sure", "yes", "no"]
                                is_invalid = any(invalid.lower() == clean_text.lower() for invalid in invalid_responses)
                                
                                logger.debug(f"[{self.job_id}] Validation check:")
                                logger.debug(f"[{self.job_id}] - clean_text: '{clean_text}'")
                                logger.debug(f"[{self.job_id}] - length: {len(clean_text)}")
                                logger.debug(f"[{self.job_id}] - is_invalid (exact match): {is_invalid}")
                                logger.debug(f"[{self.job_id}] - starts with please: {clean_text.lower().startswith('please')}")
                                logger.debug(f"[{self.job_id}] - starts with 'i ': {clean_text.lower().startswith('i ')}")
                                logger.debug(f"[{self.job_id}] - contains '?': {'?' in clean_text}")
                                
                                if (clean_text and
                                    len(clean_text) > 5 and
                                    not is_invalid and
                                    not clean_text.lower().startswith("please") and
                                    not clean_text.lower().startswith("i ") and
                                    not "?" in clean_text):
                                    search_query = clean_text
                                    logger.info(f"[{self.job_id}] Valid search query extracted: '{search_query}'")
                                    break
                                else:
                                    logger.warning(f"[{self.job_id}] Invalid response detected: '{clean_text}' - will trigger fallback")
                
                # If we didn't get a valid query, use fallback
                if not search_query:
                    logger.warning(f"[{self.job_id}] No valid search query extracted from agent response, using fallback")
                    logger.debug(f"[{self.job_id}] Fallback inputs - business_desc: '{business_desc}', target_market: '{target_market}', industry_focus: '{industry_focus}'")
                    search_query = self._generate_search_query_directly(business_desc, target_market, industry_focus)
                    logger.info(f"[{self.job_id}] Generated fallback query: '{search_query}'")
                else:
                    logger.info(f"[{self.job_id}] Using agent-generated query: '{search_query}'")
            
            logger.info(f"[{self.job_id}] Refined query: {search_query}")

            yield StatusUpdateEvent(
                event_type="status_update",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                status_message=f"Harvester query refined to: {search_query}",
                agent_name=harvester_query_refiner_agent.name
            ).to_dict()

            # Search for leads
            max_leads = self.business_context.get("max_leads_to_generate", 10)
            lead_count = 0
            search_content = types.Content(parts=[types.Part(text=search_query)])
            
            logger.info(f"[{self.job_id}] Starting lead search with query: {search_query}")
            
            async for lead_chunk in search_runner.run_async(
                user_id=self.user_id,
                session_id=session_id,
                new_message=search_content,
            ):
                logger.debug(f"[{self.job_id}] Received lead_chunk: {type(lead_chunk)}")
                
                if hasattr(lead_chunk, 'content'):
                    content = lead_chunk.content
                    logger.debug(f"[{self.job_id}] Lead chunk content type: {type(content)}")
                    logger.debug(f"[{self.job_id}] Lead chunk content: {str(content)[:500]}...")
                    
                    # Handle different content types
                    leads_data = None
                    if isinstance(content, list):
                        leads_data = content
                    elif isinstance(content, str):
                        try:
                            # Try to parse as JSON if it's a string
                            import json
                            leads_data = json.loads(content)
                            if not isinstance(leads_data, list):
                                leads_data = [leads_data] if leads_data else []
                        except json.JSONDecodeError:
                            logger.warning(f"[{self.job_id}] Could not parse lead content as JSON: {content[:200]}...")
                            continue
                    elif hasattr(content, 'parts') and content.parts:
                        # Handle different types of parts
                        for part in content.parts:
                            if hasattr(part, 'function_response') and part.function_response:
                                # Extract data from function response
                                func_response = part.function_response
                                if hasattr(func_response, 'response') and func_response.response:
                                    response_data = func_response.response
                                    if isinstance(response_data, dict) and 'result' in response_data:
                                        result = response_data['result']
                                        if isinstance(result, list):
                                            leads_data = result
                                            logger.info(f"[{self.job_id}] Extracted {len(leads_data)} leads from function response")
                                            break
                            elif hasattr(part, 'text') and part.text:
                                # Try to parse text content as JSON
                                text_content = part.text
                                try:
                                    import json
                                    leads_data = json.loads(text_content)
                                    if not isinstance(leads_data, list):
                                        leads_data = [leads_data] if leads_data else []
                                except json.JSONDecodeError:
                                    logger.warning(f"[{self.job_id}] Could not parse part text as JSON: {text_content[:200]}...")
                                    continue
                    
                    if leads_data:
                        logger.info(f"[{self.job_id}] Processing {len(leads_data)} leads from chunk")
                        for lead in leads_data:
                            if lead_count >= max_leads:
                                break
                            
                            logger.debug(f"[{self.job_id}] Processing lead: {lead}")
                            
                            # Ensure lead has required fields and extract from various formats
                            if isinstance(lead, dict):
                                # Extract and normalize fields
                                company_name = (
                                    lead.get("company_name") or
                                    lead.get("title") or
                                    lead.get("name") or
                                    "Unknown"
                                )
                                
                                website_url = (
                                    lead.get("website") or
                                    lead.get("url") or
                                    lead.get("source_url") or
                                    ""
                                )
                                
                                description = (
                                    lead.get("description") or
                                    lead.get("snippet") or
                                    lead.get("qualification_summary") or
                                    lead.get("full_content") or
                                    ""
                                )
                                
                                # Only process leads with valid websites
                                if website_url and not any(invalid in website_url.lower() for invalid in ["example.com", "localhost", "127.0.0.1"]):
                                    normalized_lead = {
                                        "company_name": company_name,
                                        "website": website_url,
                                        "description": description,
                                        "snippet": description[:200] if description else "",
                                        "source_url": website_url
                                    }
                                    
                                    logger.info(f"[{self.job_id}] Yielding lead: {company_name} - {website_url}")
                                    yield normalized_lead
                                    lead_count += 1
                                else:
                                    logger.warning(f"[{self.job_id}] Skipping lead with invalid/missing website: {website_url}")
                            else:
                                logger.warning(f"[{self.job_id}] Skipping non-dict lead: {type(lead)}")
                    else:
                        logger.warning(f"[{self.job_id}] No valid leads data found in chunk")
                else:
                    logger.warning(f"[{self.job_id}] Lead chunk has no content attribute")
                
                if lead_count >= max_leads:
                    logger.info(f"[{self.job_id}] Harvester reached max leads ({max_leads}).")
                    break
            
            if lead_count == 0:
                logger.warning(f"[{self.job_id}] No leads were generated by the harvester")
                # Don't yield any leads if none were found - let the pipeline handle this gracefully
                return
        
        except Exception as e:
            logger.error(f"[{self.job_id}] Harvester failed: {e}\n{traceback.format_exc()}")
            yield PipelineErrorEvent(
                event_type="pipeline_error",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                error_message=f"Harvester failed: {e}",
                error_type=type(e).__name__,
                agent_name="Harvester"
            ).to_dict()
        finally:
            logger.info(f"[{self.job_id}] Harvester finished.")


    async def _enrich_lead(self, lead_data: Dict[str, Any], lead_id: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Runs the full enhancement pipeline on a single lead.
        """
        yield LeadEnrichmentStartEvent(
            event_type="lead_enrichment_start",
            timestamp=datetime.now().isoformat(),
            job_id=self.job_id,
            user_id=self.user_id,
            lead_id=lead_id,
            company_name=lead_data.get("company_name", "N/A")
        ).to_dict()

        try:
            # 1. Intake - Extract proper URL and data
            website_url = (
                lead_data.get("website") or
                lead_data.get("url") or
                lead_data.get("source_url") or
                "http://example.com"
            )
            
            company_name = (
                lead_data.get("company_name") or
                lead_data.get("title") or
                website_url.replace("http://", "").replace("https://", "").split("/")[0]
            )
            
            description = (
                lead_data.get("description") or
                lead_data.get("snippet") or
                lead_data.get("search_snippet") or
                lead_data.get("full_content") or
                ""
            )
            
            logger.info(f"[{self.job_id}] Enriching lead: {company_name} at {website_url}")
            
            site_data = SiteData(
                url=website_url,
                extracted_text_content=description,
                google_search_data=GoogleSearchData(
                    title=company_name,
                    snippet=description[:500] if description else ""
                ),
                extraction_status_message="SUCCESS"
            )
            validated_lead = self.lead_intake_agent.execute(site_data)
            if not validated_lead.is_valid:
                raise ValueError(f"Lead intake failed: {validated_lead.validation_errors}")

            # 2. Initial Analysis
            analyzed_lead = self.lead_analysis_agent.execute(validated_lead)

            # 3. Full Enrichment
            # The enhanced_processor itself yields events, so we can pass them through
            async for event in self.enhanced_lead_processor.execute_enrichment_pipeline(
                analyzed_lead=analyzed_lead,
                job_id=self.job_id,
                user_id=self.user_id
            ):
                # Add lead_id to every event for frontend tracking
                event["lead_id"] = lead_id
                yield event
            
            # The final event from the enrichment pipeline is PipelineEndEvent,
            # which contains the full package. We'll capture that here.
            final_package = event.get("data")

            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=True,
                final_package=final_package
            ).to_dict()

        except Exception as e:
            logger.error(f"Enrichment failed for lead {lead_id}: {e}\n{traceback.format_exc()}")
            yield LeadEnrichmentEndEvent(
                event_type="lead_enrichment_end",
                timestamp=datetime.now().isoformat(),
                job_id=self.job_id,
                user_id=self.user_id,
                lead_id=lead_id,
                success=False,
                error_message=str(e)
            ).to_dict()