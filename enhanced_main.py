#!/usr/bin/env python3
"""
Enhanced Nellia Prospector - Multi-mode processing with comprehensive intelligence
Integrates features from new-cw.py and ck.py for advanced lead processing
"""

import os
import sys
import json
import time
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from loguru import logger
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Core imports
from core_logic.llm_client import LLMClientFactory, LLMClientBase
from data_models.lead_structures import (
    HarvesterOutput, 
    AnalyzedLead,
    ComprehensiveProspectPackage,
    ValidatedLead
)
from agents.lead_intake_agent import LeadIntakeAgent
from agents.lead_analysis_agent import LeadAnalysisAgent
from agents.enhanced_lead_processor import EnhancedLeadProcessor

class ProcessingMode(Enum):
    """Processing mode selection"""
    STANDARD = "standard"      # Original 2-agent pipeline
    ENHANCED = "enhanced"      # New comprehensive processing
    HYBRID = "hybrid"         # Both modes for comparison

@dataclass
class ProcessingResults:
    """Processing results container"""
    mode: ProcessingMode
    total_leads: int
    successful_leads: int
    failed_leads: int
    processing_time: float
    results: List[Dict[str, Any]]
    metrics: Dict[str, Any]

class EnhancedNelliaProspector:
    """
    Enhanced Nellia Prospector with multi-mode processing capabilities
    """
    
    def __init__(
        self,
        product_service_context: str,
        competitors_list: str = "",
        processing_mode: ProcessingMode = ProcessingMode.ENHANCED,
        tavily_api_key: Optional[str] = None
    ):
        self.product_service_context = product_service_context
        self.competitors_list = competitors_list
        self.processing_mode = processing_mode
        self.console = Console()
        
        # Initialize LLM client
        self.llm_client = LLMClientFactory.create_from_env()
        
        # Initialize agents
        self._initialize_agents(tavily_api_key)
        
        # Processing configuration
        self.max_concurrent_leads = 5
        self.rate_limit_delay = 1.0
        
    def _initialize_agents(self, tavily_api_key: Optional[str]):
        """Initialize processing agents based on mode"""
        
        # Standard agents (always needed)
        self.lead_intake_agent = LeadIntakeAgent(llm_client=self.llm_client)
        self.lead_analysis_agent = LeadAnalysisAgent(
            product_service_context=self.product_service_context,
            llm_client=self.llm_client
        )
        
        # Enhanced agent (for enhanced/hybrid modes)
        if self.processing_mode in [ProcessingMode.ENHANCED, ProcessingMode.HYBRID]:
            self.enhanced_processor = EnhancedLeadProcessor( # No temperature argument
                llm_client=self.llm_client, # Ensure llm_client is passed correctly
                product_service_context=self.product_service_context,
                competitors_list=self.competitors_list,
                tavily_api_key=tavily_api_key
            )
    
    def process_leads(
        self, 
        harvester_data: HarvesterOutput, 
        limit: Optional[int] = None
    ) -> ProcessingResults:
        """
        Process leads using selected mode
        """
        start_time = time.time()
        
        leads_to_process = harvester_data.sites_data
        if limit:
            leads_to_process = leads_to_process[:limit]
        
        self.console.print(Panel(
            f"🚀 Enhanced Nellia Prospector\n"
            f"Mode: {self.processing_mode.value.upper()}\n"
            f"Leads to process: {len(leads_to_process)}\n"
            f"Product/Service: {self.product_service_context[:100]}{'...' if len(self.product_service_context) > 100 else ''}",
            title="Processing Configuration",
            border_style="green"
        ))
        
        if self.processing_mode == ProcessingMode.HYBRID:
            return self._hybrid_processing(leads_to_process, start_time)
        elif self.processing_mode == ProcessingMode.ENHANCED:
            return self._enhanced_processing(leads_to_process, start_time)
        else:
            return self._standard_processing(leads_to_process, start_time)
    
    def _standard_processing(self, leads_to_process: List, start_time: float) -> ProcessingResults:
        """Run standard 2-agent pipeline"""
        
        results = []
        successful = 0
        failed = 0
        
        with Progress() as progress:
            task = progress.add_task("[blue]Standard Processing...", total=len(leads_to_process))
            
            for site_data in leads_to_process:
                try:
                    progress.update(task, description=f"[blue]Processing {site_data.url}")
                    
                    # Step 1: Lead Intake & Validation
                    validated_lead = self.lead_intake_agent.execute(site_data)
                    if not validated_lead.is_valid:
                        failed += 1
                        progress.advance(task)
                        continue
                    
                    # Step 2: Lead Analysis
                    analyzed_lead = self.lead_analysis_agent.execute(validated_lead)
                    if analyzed_lead.analysis.relevance_score < 0.3:
                        failed += 1
                        progress.advance(task)
                        continue
                    
                    # Create result
                    result = {
                        "url": str(site_data.url),
                        "company_name": self._extract_company_name_from_analyzed(analyzed_lead),
                        "processing_mode": "standard",
                        "relevance_score": analyzed_lead.analysis.relevance_score,
                        "sector": analyzed_lead.analysis.company_sector,
                        "services": analyzed_lead.analysis.main_services,
                        "challenges": analyzed_lead.analysis.potential_challenges,
                        "status": "analyzed"
                    }
                    
                    results.append(result)
                    successful += 1
                    
                except Exception as e:
                    logger.error(f"Standard processing failed for {site_data.url}: {e}")
                    failed += 1
                
                progress.advance(task)
                time.sleep(self.rate_limit_delay)
        
        total_time = time.time() - start_time
        
        return ProcessingResults(
            mode=ProcessingMode.STANDARD,
            total_leads=len(leads_to_process),
            successful_leads=successful,
            failed_leads=failed,
            processing_time=total_time,
            results=results,
            metrics={
                "avg_processing_time": total_time / len(leads_to_process),
                "success_rate": successful / len(leads_to_process),
                "total_tokens_used": self.llm_client.get_usage_stats()["total_tokens"]
            }
        )
    
    def _enhanced_processing(self, leads_to_process: List, start_time: float) -> ProcessingResults:
        """Run enhanced comprehensive pipeline"""
        
        results = []
        successful = 0
        failed = 0
        
        with Progress() as progress:
            task = progress.add_task("[green]Enhanced Processing...", total=len(leads_to_process))
            
            for site_data in leads_to_process:
                try:
                    progress.update(task, description=f"[green]Enhanced processing {site_data.url}")
                    
                    # Step 1: Lead Intake & Validation
                    validated_lead = self.lead_intake_agent.execute(site_data)
                    if not validated_lead.is_valid:
                        failed += 1
                        progress.advance(task)
                        continue
                    
                    # Step 2: Lead Analysis
                    analyzed_lead = self.lead_analysis_agent.execute(validated_lead)
                    if analyzed_lead.analysis.relevance_score < 0.3:
                        failed += 1
                        progress.advance(task)
                        continue
                    
                    # Step 3: Enhanced Processing
                    comprehensive_package = self.enhanced_processor.process(analyzed_lead)
                    
                    # Create enhanced result
                    # Create enhanced result dictionary
                    result = {
                        "url": str(site_data.url),
                        "company_name": comprehensive_package.processing_metadata.get("company_name", "Unknown"),
                        "processing_mode": "enhanced",
                        "overall_confidence_score": comprehensive_package.confidence_score,
                        "roi_potential_score": comprehensive_package.roi_potential_score,
                        "brazilian_market_fit": comprehensive_package.brazilian_market_fit,
                        "status": "enhanced_complete",
                        "processing_time_seconds": comprehensive_package.processing_metadata.get("total_processing_time", 0),
                    }

                    es = comprehensive_package.enhanced_strategy
                    if es:
                        # Lead Qualification
                        if es.lead_qualification and not es.lead_qualification.error_message:
                            result["qualification_tier"] = es.lead_qualification.qualification_tier
                            result["qualification_justification"] = es.lead_qualification.justification
                            result["qualification_confidence"] = es.lead_qualification.confidence_score
                        else:
                            result["qualification_tier"] = "Error"
                            result["qualification_justification"] = es.lead_qualification.error_message if es.lead_qualification else "N/A"
                        
                        # Pain Point Analysis
                        if es.pain_point_analysis and not es.pain_point_analysis.error_message:
                            result["primary_pain_category"] = es.pain_point_analysis.primary_pain_category
                            result["pain_urgency_level"] = es.pain_point_analysis.urgency_level
                            result["num_detailed_pain_points"] = len(es.pain_point_analysis.detailed_pain_points)
                        else:
                            result["primary_pain_category"] = "Error"
                            result["pain_urgency_level"] = es.pain_point_analysis.error_message if es.pain_point_analysis else "N/A"

                        # ToT Synthesized Action Plan
                        if es.tot_synthesized_action_plan and not es.tot_synthesized_action_plan.error_message:
                            result["recommended_strategy_name"] = es.tot_synthesized_action_plan.recommended_strategy_name
                            result["recommended_strategy_hook"] = es.tot_synthesized_action_plan.primary_angle_hook
                            result["recommended_strategy_tone"] = es.tot_synthesized_action_plan.tone_of_voice
                            result["num_action_steps"] = len(es.tot_synthesized_action_plan.action_sequence)
                        else:
                            result["recommended_strategy_name"] = "Error"
                            result["recommended_strategy_hook"] = es.tot_synthesized_action_plan.error_message if es.tot_synthesized_action_plan else "N/A"

                        # Detailed Approach Plan
                        if es.detailed_approach_plan and not es.detailed_approach_plan.error_message:
                            result["detailed_plan_main_objective"] = es.detailed_approach_plan.main_objective
                            result["num_contact_sequence_steps"] = len(es.detailed_approach_plan.contact_sequence)
                        else:
                            result["detailed_plan_main_objective"] = "Error"
                            
                        # Contact Information
                        if es.contact_information and not es.contact_information.error_message:
                            result["contacts_emails_found"] = len(es.contact_information.emails_found)
                            result["contacts_instagram_found"] = len(es.contact_information.instagram_profiles)
                            result["contact_extraction_confidence"] = es.contact_information.extraction_confidence
                        
                        # External Intelligence
                        if es.external_intelligence and not es.external_intelligence.error_message:
                            result["tavily_enriched"] = bool(es.external_intelligence.tavily_enrichment and "enrichment failed" not in es.external_intelligence.tavily_enrichment.lower())
                            result["enrichment_confidence"] = es.external_intelligence.enrichment_confidence
                        
                        # Value Propositions
                        if es.value_propositions: # This is a list
                            valid_vps = [vp for vp in es.value_propositions if not vp.error_message]
                            result["num_value_propositions"] = len(valid_vps)
                            if not valid_vps and es.value_propositions and es.value_propositions[0].error_message: # If all have errors
                                result["value_propositions_error"] = es.value_propositions[0].error_message

                        # Strategic Questions
                        result["num_strategic_questions"] = len(es.strategic_questions) if es.strategic_questions and isinstance(es.strategic_questions, list) and not (len(es.strategic_questions) == 1 and "Error" in es.strategic_questions[0]) else 0
                        
                        # Competitor Intelligence
                        if es.competitor_intelligence and not es.competitor_intelligence.error_message:
                             result["num_competitors_identified"] = len(es.competitor_intelligence.identified_competitors)
                        
                        # Purchase Triggers
                        if es.purchase_triggers and not es.purchase_triggers.error_message:
                            result["num_purchase_triggers"] = len(es.purchase_triggers.identified_triggers)

                        # Objection Framework
                        if es.objection_framework and not es.objection_framework.error_message:
                            result["num_objections_prepared"] = len(es.objection_framework.anticipated_objections)
                    else:
                        result["enhanced_strategy_error"] = "EnhancedStrategy object not populated."

                    # Personalized Message details
                    pm = comprehensive_package.enhanced_personalized_message
                    if pm and not pm.error_message and pm.primary_message:
                        result["message_channel"] = pm.primary_message.channel.value if pm.primary_message.channel else None
                        result["message_subject_present"] = bool(pm.primary_message.subject_line)
                        result["message_personalization_score"] = pm.personalization_score
                    elif pm and pm.error_message:
                         result["message_error"] = pm.error_message
                    
                    # Internal Briefing
                    ib = comprehensive_package.internal_briefing
                    if ib and not ib.error_message:
                        result["internal_briefing_executive_summary_present"] = bool(ib.executive_summary and ib.executive_summary != "Não especificado")
                    elif ib and ib.error_message:
                        result["internal_briefing_error"] = ib.error_message
                        
                    results.append(result)
                    successful += 1
                    
                except Exception as e:
                    logger.error(f"Enhanced processing failed for {site_data.url}: {e}")
                    failed += 1
                
                progress.advance(task)
                time.sleep(self.rate_limit_delay)
        
        total_time = time.time() - start_time
        
        return ProcessingResults(
            mode=ProcessingMode.ENHANCED,
            total_leads=len(leads_to_process),
            successful_leads=successful,
            failed_leads=failed,
            processing_time=total_time,
            results=results,
            metrics={
                "avg_processing_time": total_time / len(leads_to_process),
                "success_rate": successful / len(leads_to_process),
                "total_tokens_used": self.llm_client.get_usage_stats()["total_tokens"],
                "avg_confidence_score": sum(r.get("confidence_score", 0) for r in results) / max(len(results), 1),
                "avg_roi_potential": sum(r.get("roi_potential_score", 0) for r in results) / max(len(results), 1),
                "high_potential_leads": len([r for r in results if r.get("qualification_tier") == "High Potential"])
            }
        )
    
    def _hybrid_processing(self, leads_to_process: List, start_time: float) -> ProcessingResults:
        """Run both pipelines for comparison"""
        
        self.console.print("[yellow]Running hybrid comparison mode...[/yellow]")
        
        # Run standard processing
        standard_results = self._standard_processing(leads_to_process[:len(leads_to_process)//2], time.time())
        
        # Run enhanced processing  
        enhanced_results = self._enhanced_processing(leads_to_process[len(leads_to_process)//2:], time.time())
        
        # Combine results
        combined_results = standard_results.results + enhanced_results.results
        
        total_time = time.time() - start_time
        
        # Create comparison metrics
        comparison_metrics = {
            "standard_success_rate": standard_results.metrics["success_rate"],
            "enhanced_success_rate": enhanced_results.metrics["success_rate"],
            "standard_avg_time": standard_results.metrics["avg_processing_time"],
            "enhanced_avg_time": enhanced_results.metrics["avg_processing_time"],
            "standard_tokens": standard_results.metrics["total_tokens_used"],
            "enhanced_tokens": enhanced_results.metrics["total_tokens_used"],
            "processing_mode_comparison": {
                "standard_leads": standard_results.successful_leads,
                "enhanced_leads": enhanced_results.successful_leads,
                "quality_improvement": enhanced_results.metrics.get("avg_confidence_score", 0) - 0.5  # Baseline comparison
            }
        }
        
        return ProcessingResults(
            mode=ProcessingMode.HYBRID,
            total_leads=len(leads_to_process),
            successful_leads=standard_results.successful_leads + enhanced_results.successful_leads,
            failed_leads=standard_results.failed_leads + enhanced_results.failed_leads,
            processing_time=total_time,
            results=combined_results,
            metrics=comparison_metrics
        )
    
    def generate_report(self, results: ProcessingResults) -> None:
        """Generate processing report"""
        
        # Summary table
        summary_table = Table(title=f"Processing Summary - {results.mode.value.upper()} Mode")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Total Leads Processed", str(results.total_leads))
        summary_table.add_row("Successful", str(results.successful_leads))
        summary_table.add_row("Failed", str(results.failed_leads))
        summary_table.add_row("Success Rate", f"{(results.successful_leads/results.total_leads)*100:.1f}%")
        summary_table.add_row("Total Processing Time", f"{results.processing_time:.2f}s")
        summary_table.add_row("Avg Time per Lead", f"{results.processing_time/results.total_leads:.2f}s")
        
        if "total_tokens_used" in results.metrics:
            summary_table.add_row("Total Tokens Used", str(results.metrics["total_tokens_used"]))
        
        self.console.print(summary_table)
        
        # Enhanced metrics (if available)
        if results.mode == ProcessingMode.ENHANCED and results.results:
            enhanced_table = Table(title="Enhanced Processing Metrics")
            enhanced_table.add_column("Metric", style="cyan")
            enhanced_table.add_column("Value", style="green")
            
            if "avg_confidence_score" in results.metrics:
                enhanced_table.add_row("Avg Confidence Score", f"{results.metrics['avg_confidence_score']:.3f}")
            if "avg_roi_potential" in results.metrics:
                enhanced_table.add_row("Avg ROI Potential", f"{results.metrics['avg_roi_potential']:.3f}")
            if "high_potential_leads" in results.metrics:
                enhanced_table.add_row("High Potential Leads", str(results.metrics['high_potential_leads']))
            
            # Qualification breakdown
            qualification_counts = {}
            for result in results.results:
                tier = result.get("qualification_tier", "Unknown")
                qualification_counts[tier] = qualification_counts.get(tier, 0) + 1
            
            for tier, count in qualification_counts.items():
                enhanced_table.add_row(f"{tier} Leads", str(count))
            
            self.console.print(enhanced_table)
        
        # Hybrid comparison (if available)
        if results.mode == ProcessingMode.HYBRID:
            comparison_table = Table(title="Pipeline Comparison")
            comparison_table.add_column("Pipeline", style="cyan")
            comparison_table.add_column("Success Rate", style="green")
            comparison_table.add_column("Avg Time", style="yellow")
            comparison_table.add_column("Tokens Used", style="blue")
            
            comparison_table.add_row(
                "Standard",
                f"{results.metrics['standard_success_rate']*100:.1f}%",
                f"{results.metrics['standard_avg_time']:.2f}s",
                str(results.metrics['standard_tokens'])
            )
            comparison_table.add_row(
                "Enhanced", 
                f"{results.metrics['enhanced_success_rate']*100:.1f}%",
                f"{results.metrics['enhanced_avg_time']:.2f}s",
                str(results.metrics['enhanced_tokens'])
            )
            
            self.console.print(comparison_table)
    
    def save_results(self, results: ProcessingResults, output_file: str) -> None:
        """Save results to JSON file"""
        
        output_data = {
            "processing_summary": {
                "mode": results.mode.value,
                "timestamp": datetime.now().isoformat(),
                "total_leads": results.total_leads,
                "successful_leads": results.successful_leads,
                "failed_leads": results.failed_leads,
                "processing_time": results.processing_time,
                "metrics": results.metrics
            },
            "configuration": {
                "product_service_context": self.product_service_context,
                "competitors_list": self.competitors_list,
                "tavily_enabled": hasattr(self, 'enhanced_processor') and bool(self.enhanced_processor.tavily_api_key)
            },
            "results": results.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        self.console.print(f"✅ Results saved to: {output_file}")
    
    def _extract_company_name_from_analyzed(self, analyzed_lead: AnalyzedLead) -> str:
        """Extract company name from analyzed lead"""
        site_data = analyzed_lead.validated_lead.site_data
        if site_data.google_search_data and site_data.google_search_data.title:
            title = site_data.google_search_data.title
            company_name = title.split(" - ")[0].split(" | ")[0].split(": ")[0]
            if len(company_name) > 5:
                return company_name.strip()
        
        # Fallback to domain
        url = str(site_data.url)
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        return domain.replace('www.', '').split('.')[0].title()

def load_harvester_data(file_path: str) -> HarvesterOutput:
    """Load harvester data from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return HarvesterOutput(**data)
    except Exception as e:
        logger.error(f"Failed to load harvester data from {file_path}: {e}")
        raise

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Enhanced Nellia Prospector - Multi-mode AI lead processing")
    
    # Required arguments
    parser.add_argument("harvester_file", help="Path to harvester output JSON file")
    parser.add_argument("-p", "--product", required=True, help="Product/service context for analysis")
    
    # Optional arguments
    parser.add_argument("-m", "--mode", choices=["standard", "enhanced", "hybrid"], 
                       default="enhanced", help="Processing mode (default: enhanced)")
    parser.add_argument("-c", "--competitors", default="", help="Known competitors list")
    parser.add_argument("-n", "--limit", type=int, help="Limit number of leads to process")
    parser.add_argument("-o", "--output", help="Output file path (default: auto-generated)")
    parser.add_argument("-l", "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level=args.log_level)
    
    try:
        # Load harvester data
        harvester_data = load_harvester_data(args.harvester_file)
        
        # Initialize processor
        processing_mode = ProcessingMode(args.mode)
        
        processor = EnhancedNelliaProspector(
            product_service_context=args.product,
            competitors_list=args.competitors,
            processing_mode=processing_mode,
            tavily_api_key=os.getenv("TAVILY_API_KEY")
        )
        
        # Process leads
        results = processor.process_leads(harvester_data, args.limit)
        
        # Generate report
        processor.generate_report(results)
        
        # Save results
        if args.output:
            output_file = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"enhanced_prospector_results_{args.mode}_{timestamp}.json"
        
        processor.save_results(results, output_file)
        
        # ROI Summary
        if results.mode == ProcessingMode.ENHANCED and results.successful_leads > 0:
            avg_confidence = results.metrics.get("avg_confidence_score", 0)
            avg_roi_potential = results.metrics.get("avg_roi_potential", 0)
            high_potential_count = results.metrics.get("high_potential_leads", 0)
            
            rprint(Panel(
                f"🎯 ROI OPTIMIZATION SUMMARY\n\n"
                f"Target: 527% ROI Achievement\n"
                f"High Potential Leads: {high_potential_count}/{results.successful_leads}\n"
                f"Avg Confidence Score: {avg_confidence:.3f}\n"
                f"Avg ROI Potential: {avg_roi_potential:.3f}\n"
                f"Brazilian Market Optimization: ENABLED\n\n"
                f"✨ Ready for high-converting outreach!",
                title="Enhanced Processing Complete",
                border_style="gold1"
            ))
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
