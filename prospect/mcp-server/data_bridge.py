"""
Data Bridge for MCP Server
Bridges MCP server simple models with prospect's rich data structures
"""

import json
import sys
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

# Add prospect directory to path for imports
prospect_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if prospect_root not in sys.path:
    sys.path.insert(0, prospect_root)

# Import from prospect's data_models package
try:
    from data_models.lead_structures import (
        ComprehensiveProspectPackage,
        AnalyzedLead,
        ValidatedLead,
        SiteData,
        GoogleSearchData,
        LeadAnalysis,
        EnhancedStrategy,
        EnhancedPersonalizedMessage,
        InternalBriefing,
        ContactInformation,
        ExternalIntelligence,
        PainPointAnalysis,
        LeadQualification,
        CompetitorIntelligence,
        PurchaseTriggers,
        ValueProposition,
        ObjectionFramework,
        PersonalizedMessage,
        CommunicationChannel
    )
except ImportError as e:
    logger.error(f"Failed to import prospect data models: {e}")
    # Create placeholder classes for development
    class ComprehensiveProspectPackage:
        pass
    class AnalyzedLead:
        pass
    class ValidatedLead:
        pass
    class SiteData:
        pass
    class GoogleSearchData:
        pass
    class LeadAnalysis:
        pass
    class EnhancedStrategy:
        pass
    class EnhancedPersonalizedMessage:
        pass
    class InternalBriefing:
        pass
    class ContactInformation:
        pass
    class ExternalIntelligence:
        pass
    class PainPointAnalysis:
        pass
    class LeadQualification:
        pass
    class CompetitorIntelligence:
        pass
    class PurchaseTriggers:
        pass
    class ValueProposition:
        pass
    class ObjectionFramework:
        pass
    class PersonalizedMessage:
        pass
    class CommunicationChannel:
        pass

# Import from local MCP schemas file
import mcp_schemas
LeadProcessingStatePydantic = mcp_schemas.LeadProcessingState
AgentExecutionRecordPydantic = mcp_schemas.AgentExecutionRecord
LeadProcessingStatusEnum = mcp_schemas.LeadProcessingStatusEnum
AgentExecutionStatusEnum = mcp_schemas.AgentExecutionStatusEnum

class DataBridge:
    """Bridge between MCP server models and prospect system data structures"""
    
    @staticmethod
    def convert_to_mcp_format(prospect_data: ComprehensiveProspectPackage) -> Dict[str, Any]:
        """Convert prospect data to MCP storage format"""
        try:
            # Extract key information for MCP storage
            analyzed_lead = prospect_data.analyzed_lead
            validated_lead = analyzed_lead.validated_lead
            site_data = validated_lead.site_data
            
            # Basic lead information
            lead_url = str(site_data.url)
            company_name = DataBridge._extract_company_name(site_data)
            
            # Create comprehensive summary for MCP storage
            mcp_data = {
                # Basic identification
                "lead_url": lead_url,
                "company_name": company_name,
                "processing_timestamp": prospect_data.processing_timestamp.isoformat(),
                
                # Core metrics
                "confidence_score": prospect_data.confidence_score,
                "roi_potential_score": prospect_data.roi_potential_score,
                "brazilian_market_fit": prospect_data.brazilian_market_fit,
                
                # Analysis summary
                "analysis_summary": {
                    "company_sector": analyzed_lead.analysis.company_sector,
                    "main_services": analyzed_lead.analysis.main_services,
                    "company_size_estimate": analyzed_lead.analysis.company_size_estimate,
                    "relevance_score": analyzed_lead.analysis.relevance_score,
                    "general_diagnosis": analyzed_lead.analysis.general_diagnosis[:500] + "..." if len(analyzed_lead.analysis.general_diagnosis) > 500 else analyzed_lead.analysis.general_diagnosis
                },
                
                # Strategy summary
                "strategy_summary": DataBridge._extract_strategy_summary(prospect_data.enhanced_strategy),
                
                # Message summary
                "message_summary": DataBridge._extract_message_summary(prospect_data.enhanced_personalized_message),
                
                # Briefing summary
                "briefing_summary": DataBridge._extract_briefing_summary(prospect_data.internal_briefing),
                
                # Processing metadata
                "processing_metadata": prospect_data.processing_metadata,
                
                # Full data (compressed JSON)
                "full_data_json": DataBridge._compress_json(prospect_data.model_dump()),
                
                # Version info
                "data_version": "1.0",
                "bridge_version": "1.0"
            }
            
            return mcp_data
            
        except Exception as e:
            logger.error(f"Failed to convert prospect data to MCP format: {e}")
            return {
                "error": str(e),
                "processing_timestamp": datetime.now().isoformat(),
                "data_version": "1.0",
                "bridge_version": "1.0"
            }
    
    @staticmethod
    def convert_from_mcp_format(mcp_data: Dict[str, Any]) -> Optional[ComprehensiveProspectPackage]:
        """Reconstruct prospect data from MCP storage"""
        try:
            # Check if full JSON data is available
            if "full_data_json" in mcp_data:
                full_data = DataBridge._decompress_json(mcp_data["full_data_json"])
                if full_data:
                    return ComprehensiveProspectPackage(**full_data)
            
            # If full data not available, construct from summary
            logger.warning("Full data not available, reconstructing from summary")
            return DataBridge._reconstruct_from_summary(mcp_data)
            
        except Exception as e:
            logger.error(f"Failed to convert MCP data to prospect format: {e}")
            return None
    
    @staticmethod
    def extract_summary_metrics(prospect_data: ComprehensiveProspectPackage) -> Dict[str, Any]:
        """Extract key metrics for MCP tracking"""
        try:
            analyzed_lead = prospect_data.analyzed_lead
            strategy = prospect_data.enhanced_strategy
            
            metrics = {
                # Basic metrics
                "confidence_score": prospect_data.confidence_score,
                "roi_potential_score": prospect_data.roi_potential_score,
                "brazilian_market_fit": prospect_data.brazilian_market_fit,
                "relevance_score": analyzed_lead.analysis.relevance_score,
                
                # Processing metrics
                "total_processing_time": prospect_data.processing_metadata.get("total_processing_time", 0),
                "processing_mode": prospect_data.processing_metadata.get("processing_mode", "unknown"),
                
                # Intelligence metrics
                "external_intelligence_confidence": strategy.external_intelligence.enrichment_confidence if strategy.external_intelligence else 0,
                "contact_extraction_confidence": strategy.contact_information.extraction_confidence if strategy.contact_information else 0,
                
                # Lead qualification
                "qualification_tier": strategy.lead_qualification.qualification_tier if strategy.lead_qualification else "unknown",
                "qualification_score": strategy.lead_qualification.qualification_score if strategy.lead_qualification else 0,
                
                # Strategy effectiveness
                "value_propositions_count": len(strategy.value_propositions) if strategy.value_propositions else 0,
                "strategic_questions_count": len(strategy.strategic_questions) if strategy.strategic_questions else 0,
                
                # Pain point analysis
                "pain_point_urgency": strategy.pain_point_analysis.urgency_level if strategy.pain_point_analysis else "unknown",
                "detailed_pain_points_count": len(strategy.pain_point_analysis.detailed_pain_points) if strategy.pain_point_analysis and strategy.pain_point_analysis.detailed_pain_points else 0,
                
                # Personalization metrics
                "personalization_score": prospect_data.enhanced_personalized_message.personalization_score,
                "message_channel": prospect_data.enhanced_personalized_message.primary_message.channel.value,
                
                # Contact information
                "emails_found": len(strategy.contact_information.emails_found) if strategy.contact_information else 0,
                "social_profiles_found": len(strategy.contact_information.instagram_profiles) if strategy.contact_information else 0,
                
                # Timestamp
                "metrics_timestamp": datetime.now().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to extract summary metrics: {e}")
            return {
                "error": str(e),
                "metrics_timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    def create_agent_execution_summary(agent_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create agent execution summary for MCP tracking"""
        try:
            summary = {
                "agent_name": agent_name,
                "success": result.get("success", False),
                "processing_time_seconds": result.get("processing_time_seconds", 0),
                "timestamp": datetime.now().isoformat(),
                "error_message": result.get("error_message")
            }
            
            # Add metrics if available
            if "metrics" in result and result["metrics"]:
                summary["metrics"] = result["metrics"]
            
            # Add result summary if available
            if result.get("result"):
                summary["result_summary"] = DataBridge._create_result_summary(agent_name, result["result"])
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to create agent execution summary: {e}")
            return {
                "agent_name": agent_name,
                "success": False,
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    @staticmethod
    def convert_site_data_to_validated_lead(site_data_dict: Dict[str, Any]) -> Optional[ValidatedLead]:
        """Convert raw site data to ValidatedLead format"""
        try:
            # Create GoogleSearchData if available
            google_data = None
            if "google_search_data" in site_data_dict:
                google_data = GoogleSearchData(**site_data_dict["google_search_data"])
            
            # Create SiteData
            site_data = SiteData(
                url=site_data_dict["url"],
                google_search_data=google_data,
                extracted_text_content=site_data_dict.get("extracted_text_content"),
                extraction_status_message=site_data_dict.get("extraction_status_message", "Unknown"),
                screenshot_filepath=site_data_dict.get("screenshot_filepath")
            )
            
            # Create ValidatedLead
            validated_lead = ValidatedLead(
                site_data=site_data,
                validation_timestamp=datetime.now(),
                is_valid=True,
                validation_errors=[],
                cleaned_text_content=site_data_dict.get("extracted_text_content"),
                extraction_successful=bool(site_data_dict.get("extracted_text_content"))
            )
            
            return validated_lead
            
        except Exception as e:
            logger.error(f"Failed to convert site data to ValidatedLead: {e}")
            return None
    
    @staticmethod
    def _extract_company_name(site_data: SiteData) -> str:
        """Extract company name from site data"""
        if site_data.google_search_data and site_data.google_search_data.title:
            title = site_data.google_search_data.title
            # Extract company name from title
            company_name = title.split(" - ")[0].split(" | ")[0].split(": ")[0]
            if len(company_name) > 5:
                return company_name.strip()
        
        # Fallback to domain name
        url = str(site_data.url)
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        domain = domain.replace('www.', '')
        return domain.split('.')[0].title()
    
    @staticmethod
    def _extract_strategy_summary(strategy: EnhancedStrategy) -> Dict[str, Any]:
        """Extract strategy summary for MCP storage"""
        summary = {}
        
        if strategy.lead_qualification:
            summary["qualification"] = {
                "tier": strategy.lead_qualification.qualification_tier,
                "score": strategy.lead_qualification.qualification_score
            }
        
        if strategy.pain_point_analysis:
            summary["pain_points"] = {
                "primary_category": strategy.pain_point_analysis.primary_pain_category,
                "urgency_level": strategy.pain_point_analysis.urgency_level,
                "count": len(strategy.pain_point_analysis.detailed_pain_points) if strategy.pain_point_analysis.detailed_pain_points else 0
            }
        
        if strategy.value_propositions:
            summary["value_propositions"] = {
                "count": len(strategy.value_propositions),
                "titles": [vp.title for vp in strategy.value_propositions if not vp.error_message][:3]  # First 3 titles
            }
        
        if strategy.tot_synthesized_action_plan:
            summary["action_plan"] = {
                "strategy_name": strategy.tot_synthesized_action_plan.recommended_strategy_name,
                "tone_of_voice": strategy.tot_synthesized_action_plan.tone_of_voice,
                "steps_count": len(strategy.tot_synthesized_action_plan.action_sequence) if strategy.tot_synthesized_action_plan.action_sequence else 0
            }
        
        return summary
    
    @staticmethod
    def _extract_message_summary(message: EnhancedPersonalizedMessage) -> Dict[str, Any]:
        """Extract message summary for MCP storage"""
        return {
            "channel": message.primary_message.channel.value,
            "subject": message.primary_message.subject_line,
            "personalization_score": message.personalization_score,
            "cultural_appropriateness_score": message.cultural_appropriateness_score,
            "estimated_response_rate": message.estimated_response_rate,
            "message_preview": message.primary_message.message_body[:200] + "..." if len(message.primary_message.message_body) > 200 else message.primary_message.message_body
        }
    
    @staticmethod
    def _extract_briefing_summary(briefing: InternalBriefing) -> Dict[str, Any]:
        """Extract briefing summary for MCP storage"""
        return {
            "executive_summary": briefing.executive_summary[:300] + "..." if len(briefing.executive_summary) > 300 else briefing.executive_summary,
            "recommended_next_step": briefing.recommended_next_step,
            "sections_available": [
                section for section in [
                    "lead_overview" if briefing.lead_overview else None,
                    "persona_profile_summary" if briefing.persona_profile_summary else None,
                    "pain_points_and_needs" if briefing.pain_points_and_needs else None,
                    "buying_triggers_opportunity" if briefing.buying_triggers_opportunity else None,
                    "lead_qualification_summary" if briefing.lead_qualification_summary else None,
                    "approach_strategy_summary" if briefing.approach_strategy_summary else None,
                    "custom_value_proposition_summary" if briefing.custom_value_proposition_summary else None,
                    "potential_objections_summary" if briefing.potential_objections_summary else None
                ] if section
            ]
        }
    
    @staticmethod
    def _compress_json(data: Dict[str, Any]) -> str:
        """Compress JSON data for storage"""
        try:
            import gzip
            import base64
            
            json_str = json.dumps(data, ensure_ascii=False, default=str)
            compressed = gzip.compress(json_str.encode('utf-8'))
            return base64.b64encode(compressed).decode('ascii')
        except Exception as e:
            logger.warning(f"Failed to compress JSON data: {e}")
            return json.dumps(data, ensure_ascii=False, default=str)
    
    @staticmethod
    def _decompress_json(compressed_data: str) -> Optional[Dict[str, Any]]:
        """Decompress JSON data from storage"""
        try:
            import gzip
            import base64
            
            # Try decompression first
            try:
                compressed = base64.b64decode(compressed_data.encode('ascii'))
                json_str = gzip.decompress(compressed).decode('utf-8')
            except:
                # If decompression fails, assume it's uncompressed JSON
                json_str = compressed_data
            
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to decompress JSON data: {e}")
            return None
    
    @staticmethod
    def _reconstruct_from_summary(mcp_data: Dict[str, Any]) -> Optional[ComprehensiveProspectPackage]:
        """Reconstruct prospect data from MCP summary (limited functionality)"""
        try:
            # This is a basic reconstruction - full functionality requires complete data
            logger.warning("Reconstructing from summary - limited data available")
            
            # Create minimal structures to satisfy the model requirements
            # This is mainly for compatibility when full data is not available
            
            # TODO: Implement full reconstruction logic when needed
            # For now, return None to indicate reconstruction is not possible
            return None
            
        except Exception as e:
            logger.error(f"Failed to reconstruct from summary: {e}")
            return None
    
    @staticmethod
    def _create_result_summary(agent_name: str, result: Any) -> Dict[str, Any]:
        """Create a summary of agent execution result"""
        try:
            if hasattr(result, 'model_dump'):
                # Pydantic model
                result_dict = result.model_dump()
                return {
                    "type": "pydantic_model",
                    "model_name": result.__class__.__name__,
                    "key_fields": list(result_dict.keys())[:10],  # First 10 fields
                    "has_error": bool(getattr(result, 'error_message', None))
                }
            elif isinstance(result, dict):
                return {
                    "type": "dict",
                    "key_fields": list(result.keys())[:10],
                    "size": len(result)
                }
            elif isinstance(result, list):
                return {
                    "type": "list",
                    "length": len(result),
                    "item_types": [type(item).__name__ for item in result[:5]]  # First 5 item types
                }
            else:
                return {
                    "type": type(result).__name__,
                    "str_representation": str(result)[:200]
                }
        except Exception as e:
            return {
                "type": "unknown",
                "error": str(e)
            }

class McpProspectDataManager:
    """Manager for handling prospect data within MCP server context"""
    
    def __init__(self):
        self.bridge = DataBridge()
        
    def store_prospect_result(self, lead_id: str, prospect_data: ComprehensiveProspectPackage) -> Dict[str, Any]:
        """Store prospect processing result in MCP format"""
        try:
            mcp_data = self.bridge.convert_to_mcp_format(prospect_data)
            summary_metrics = self.bridge.extract_summary_metrics(prospect_data)
            
            return {
                "lead_id": lead_id,
                "storage_data": mcp_data,
                "summary_metrics": summary_metrics,
                "storage_timestamp": datetime.now().isoformat(),
                "success": True
            }
        except Exception as e:
            logger.error(f"Failed to store prospect result for {lead_id}: {e}")
            return {
                "lead_id": lead_id,
                "success": False,
                "error": str(e),
                "storage_timestamp": datetime.now().isoformat()
            }
    
    def retrieve_prospect_result(self, mcp_data: Dict[str, Any]) -> Optional[ComprehensiveProspectPackage]:
        """Retrieve prospect processing result from MCP data"""
        return self.bridge.convert_from_mcp_format(mcp_data)
    
    def create_processing_summary(self, prospect_data: ComprehensiveProspectPackage) -> str:
        """Create a human-readable processing summary"""
        try:
            analyzed_lead = prospect_data.analyzed_lead
            strategy = prospect_data.enhanced_strategy
            message = prospect_data.enhanced_personalized_message
            
            summary_parts = [
                f"Lead: {self.bridge._extract_company_name(analyzed_lead.validated_lead.site_data)}",
                f"Confidence: {prospect_data.confidence_score:.2f}",
                f"ROI Potential: {prospect_data.roi_potential_score:.2f}",
                f"Qualification: {strategy.lead_qualification.qualification_tier if strategy.lead_qualification else 'Unknown'}",
                f"Channel: {message.primary_message.channel.value}",
                f"Personalization: {message.personalization_score:.2f}"
            ]
            
            return " | ".join(summary_parts)
            
        except Exception as e:
            logger.error(f"Failed to create processing summary: {e}")
            return f"Processing Summary Error: {str(e)}"
