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
import traceback # Added import for traceback
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field # ensure field is imported
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
    ValidatedLead,
    SiteData, # Added SiteData for create_test_data
    GoogleSearchData # Added GoogleSearchData for create_test_data
)
from agents.lead_intake_agent import LeadIntakeAgent
from agents.lead_analysis_agent import LeadAnalysisAgent
from agents.enhanced_lead_processor import EnhancedLeadProcessor

class ProcessingMode(Enum):
    """Processing mode selection"""
    STANDARD = "standard"
    ENHANCED = "enhanced"
    HYBRID = "hybrid"

@dataclass
class ProcessingResults:
    """Processing results container"""
    mode: ProcessingMode
    total_leads: int
    successful_leads: int
    failed_leads: int
    processing_time: float
    results: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

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
        
        self.llm_client = LLMClientFactory.create_from_env()
        self._initialize_agents(tavily_api_key)
        
        self.max_concurrent_leads = 5 # Example: process 5 leads concurrently in async mode
        self.rate_limit_delay = 1.0 # Seconds to wait between synchronous calls

    def _initialize_agents(self, tavily_api_key: Optional[str]):
        self.lead_intake_agent = LeadIntakeAgent(llm_client=self.llm_client)
        self.lead_analysis_agent = LeadAnalysisAgent(
            product_service_context=self.product_service_context,
            llm_client=self.llm_client
        )
        if self.processing_mode in [ProcessingMode.ENHANCED, ProcessingMode.HYBRID]:
            self.enhanced_processor = EnhancedLeadProcessor(
                llm_client=self.llm_client,
                product_service_context=self.product_service_context,
                competitors_list=self.competitors_list,
                tavily_api_key=tavily_api_key
            )
    
    def process_leads(
        self, 
        harvester_data: HarvesterOutput, 
        limit: Optional[int] = None
    ) -> ProcessingResults:
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
            # For hybrid, we might want to split the list or run both on all
            # For simplicity now, it will run both on the limited set
            standard_results_list = self._standard_processing(leads_to_process, start_time, is_hybrid_component=True).results
            enhanced_results_list = self._enhanced_processing(leads_to_process, start_time, is_hybrid_component=True).results
            # Note: Metrics might be a bit mixed up here if not careful with timing and token counts.
            # This part needs careful thought for meaningful hybrid metrics.
            # For now, focusing on getting the output structure.
            combined_results = {"standard": standard_results_list, "enhanced": enhanced_results_list}
            # This result structure for HYBRID is different and generate_report needs to handle it.
            # Or, adapt to return a single list with mode indicated in each item.
            # For now, let's return a combined list with mode indicated in each item.
            all_results = []
            for r in standard_results_list:
                r['actual_processing_mode'] = ProcessingMode.STANDARD.value
                all_results.append(r)
            for r in enhanced_results_list:
                r['actual_processing_mode'] = ProcessingMode.ENHANCED.value
                all_results.append(r)

            return ProcessingResults(
                mode=ProcessingMode.HYBRID,
                total_leads=len(leads_to_process) * 2, # Each lead processed twice
                successful_leads=len(standard_results_list) + len(enhanced_results_list), # Approximation
                failed_leads=0, # Approximation
                processing_time=time.time() - start_time,
                results=all_results, # Combined
                metrics={} # TODO: Define meaningful hybrid metrics
            )

        elif self.processing_mode == ProcessingMode.ENHANCED:
            return self._enhanced_processing(leads_to_process, start_time)
        else: # STANDARD
            return self._standard_processing(leads_to_process, start_time)

    def _standard_processing(self, leads_to_process: List[SiteData], start_time: float, is_hybrid_component: bool = False) -> ProcessingResults:
        results = []
        successful = 0
        failed = 0
        
        with Progress(console=self.console, transient=True) as progress:
            task = progress.add_task("[blue]Standard Processing...", total=len(leads_to_process))
            for site_data in leads_to_process:
                progress.update(task, description=f"[blue]Std Proc: {str(site_data.url)[:50]}...")
                try:
                    validated_lead = self.lead_intake_agent.execute(site_data)
                    if not validated_lead.is_valid:
                        failed += 1; progress.advance(task); continue
                    
                    analyzed_lead = self.lead_analysis_agent.execute(validated_lead)
                    if analyzed_lead.analysis.relevance_score < 0.3: # Example filter
                        failed += 1; progress.advance(task); continue
                    
                    result = {
                        "url": str(site_data.url),
                        "company_name": self._extract_company_name_from_analyzed(analyzed_lead),
                        "relevance_score": analyzed_lead.analysis.relevance_score,
                        "sector": analyzed_lead.analysis.company_sector,
                        "services": analyzed_lead.analysis.main_services,
                        "challenges": analyzed_lead.analysis.potential_challenges,
                        "status": "standard_processed"
                    }
                    results.append(result)
                    successful += 1
                except Exception as e:
                    logger.error(f"Standard processing failed for {site_data.url}: {e}")
                    failed += 1
                progress.advance(task)
                if not is_hybrid_component: time.sleep(self.rate_limit_delay)
        
        return ProcessingResults(
            mode=ProcessingMode.STANDARD, total_leads=len(leads_to_process),
            successful_leads=successful, failed_leads=failed,
            processing_time=time.time() - start_time, results=results,
            metrics={"avg_processing_time": (time.time() - start_time) / max(1,len(leads_to_process)),
                     "success_rate": successful / max(1,len(leads_to_process)),
                     "total_tokens_used": self.llm_client.get_usage_stats()["total_tokens"]}
        )

    def _enhanced_processing(self, leads_to_process: List[SiteData], start_time: float, is_hybrid_component: bool = False) -> ProcessingResults:
        results = []
        successful = 0
        failed = 0
        
        with Progress(console=self.console, transient=True) as progress:
            task = progress.add_task("[green]Enhanced Processing...", total=len(leads_to_process))
            for site_data in leads_to_process:
                progress.update(task, description=f"[green]Enh Proc: {str(site_data.url)[:50]}...")
                try:
                    validated_lead = self.lead_intake_agent.execute(site_data)
                    if not validated_lead.is_valid:
                        failed += 1; progress.advance(task); continue
                    
                    analyzed_lead = self.lead_analysis_agent.execute(validated_lead)
                    if analyzed_lead.analysis.relevance_score < 0.1: # Lower threshold for enhanced as it might find more
                        failed += 1; progress.advance(task); continue
                    
                    comprehensive_package = self.enhanced_processor.execute(analyzed_lead) # Using BaseAgent's execute
                    
                    result = {
                        "url": str(site_data.url),
                        "company_name": comprehensive_package.processing_metadata.get("company_name", "Unknown"),
                        "overall_confidence_score": comprehensive_package.confidence_score,
                        "roi_potential_score": comprehensive_package.roi_potential_score,
                        "brazilian_market_fit": comprehensive_package.brazilian_market_fit,
                        "status": "enhanced_complete",
                        "processing_time_seconds": comprehensive_package.processing_metadata.get("total_processing_time", 0),
                    }
                    es = comprehensive_package.enhanced_strategy
                    if es:
                        if es.lead_qualification and not es.lead_qualification.error_message:
                            result["qualification_tier"] = es.lead_qualification.qualification_tier
                            result["qualification_justification"] = es.lead_qualification.justification
                        if es.pain_point_analysis and not es.pain_point_analysis.error_message:
                            result["primary_pain_category"] = es.pain_point_analysis.primary_pain_category
                            result["pain_urgency_level"] = es.pain_point_analysis.urgency_level
                            result["num_detailed_pain_points"] = len(es.pain_point_analysis.detailed_pain_points or [])
                        if es.tot_synthesized_action_plan and not es.tot_synthesized_action_plan.error_message:
                            result["recommended_strategy_name"] = es.tot_synthesized_action_plan.recommended_strategy_name
                        if es.detailed_approach_plan and not es.detailed_approach_plan.error_message:
                            result["detailed_plan_main_objective"] = es.detailed_approach_plan.main_objective
                        if es.contact_information and not es.contact_information.error_message:
                            result["contacts_emails_found"] = len(es.contact_information.emails_found or [])
                        if es.external_intelligence and not es.external_intelligence.error_message:
                            result["tavily_enriched"] = bool(es.external_intelligence.tavily_enrichment and "enrichment failed" not in es.external_intelligence.tavily_enrichment.lower())
                        if es.value_propositions:
                            result["num_value_propositions"] = len([vp for vp in es.value_propositions if not vp.error_message])
                        if es.strategic_questions: result["num_strategic_questions"] = len(es.strategic_questions)
                        if es.competitor_intelligence and not es.competitor_intelligence.error_message:
                             result["num_competitors_identified"] = len(es.competitor_intelligence.identified_competitors or [])
                        if es.purchase_triggers and not es.purchase_triggers.error_message:
                            result["num_purchase_triggers"] = len(es.purchase_triggers.identified_triggers or [])
                        if es.objection_framework and not es.objection_framework.error_message:
                            result["num_objections_prepared"] = len(es.objection_framework.anticipated_objections or [])
                    pm = comprehensive_package.enhanced_personalized_message
                    if pm and not pm.error_message and pm.primary_message:
                        result["message_channel"] = pm.primary_message.channel.value if pm.primary_message.channel else None
                    ib = comprehensive_package.internal_briefing
                    if ib and not ib.error_message:
                        result["internal_briefing_executive_summary_present"] = bool(ib.executive_summary and ib.executive_summary != "Não especificado")

                    # Add content marketing information
                    cm_ideas = comprehensive_package.enhanced_strategy.content_marketing_ideas
                    if cm_ideas and (not cm_ideas.generation_summary or "error" not in cm_ideas.generation_summary.lower()):
                        result["content_marketing_num_blog_ideas"] = len(cm_ideas.blog_post_ideas or [])
                        if cm_ideas.blog_post_ideas:
                            result["content_marketing_sample_blog_title"] = cm_ideas.blog_post_ideas[0].title
                        result["content_marketing_num_social_posts"] = len(cm_ideas.social_media_posts or [])
                        if cm_ideas.social_media_posts:
                            result["content_marketing_sample_social_platform"] = cm_ideas.social_media_posts[0].platform
                            result["content_marketing_sample_social_text_preview"] = cm_ideas.social_media_posts[0].post_text[:50] + "..."
                        result["content_marketing_num_seo_keywords"] = len(cm_ideas.suggested_seo_keywords or [])
                        result["content_marketing_generated"] = True
                    else:
                        result["content_marketing_generated"] = False
                        if cm_ideas and cm_ideas.generation_summary:
                             result["content_marketing_error"] = cm_ideas.generation_summary

                    results.append(result); successful += 1
                except Exception as e:
                    logger.error(f"Enhanced processing failed for {site_data.url}: {e}\n{traceback.format_exc()}")
                    failed += 1
                progress.advance(task)
                if not is_hybrid_component: time.sleep(self.rate_limit_delay)

        return ProcessingResults(
            mode=ProcessingMode.ENHANCED, total_leads=len(leads_to_process),
            successful_leads=successful, failed_leads=failed,
            processing_time=time.time() - start_time, results=results,
            metrics={
                "avg_processing_time": (time.time() - start_time) / max(1,len(leads_to_process)),
                "success_rate": successful / max(1,len(leads_to_process)),
                "total_tokens_used": self.llm_client.get_usage_stats()["total_tokens"],
                "avg_overall_confidence_score": sum(r.get("overall_confidence_score", 0) for r in results if r.get("overall_confidence_score") is not None) / max(1, successful),
                "avg_roi_potential": sum(r.get("roi_potential_score", 0) for r in results if r.get("roi_potential_score") is not None) / max(1, successful),
                "high_potential_leads": len([r for r in results if r.get("qualification_tier") == "Alto Potencial" or r.get("qualification_tier") == "High Potential"]) # Adjusted for new Pydantic
            }
        )
    
    def generate_report(self, results: ProcessingResults) -> None:
        self.console.rule(f"[bold cyan]Processing Report - {results.mode.value.upper()} Mode[/bold cyan]")
        
        summary_table = Table(title="Overall Summary")
        summary_table.add_column("Metric", style="dim cyan")
        summary_table.add_column("Value", style="bold green")
        summary_table.add_row("Total Leads Input", str(results.total_leads))
        summary_table.add_row("Successfully Processed", str(results.successful_leads))
        summary_table.add_row("Failed to Process", str(results.failed_leads))
        if results.total_leads > 0:
            summary_table.add_row("Success Rate", f"{(results.successful_leads/results.total_leads)*100:.1f}%")
        summary_table.add_row("Total Processing Time", f"{results.processing_time:.2f}s")
        if results.total_leads > 0:
            summary_table.add_row("Avg Time per Lead", f"{results.processing_time/results.total_leads:.2f}s")
        if "total_tokens_used" in results.metrics:
            summary_table.add_row("Total LLM Tokens Used", str(results.metrics["total_tokens_used"]))
        self.console.print(summary_table)

        if results.mode == ProcessingMode.ENHANCED and results.results and results.successful_leads > 0:
            enhanced_metrics_table = Table(title="Enhanced Processing Aggregate Metrics")
            enhanced_metrics_table.add_column("Aggregate Metric", style="dim cyan")
            enhanced_metrics_table.add_column("Value", style="bold green")
            
            if "avg_overall_confidence_score" in results.metrics:
                enhanced_metrics_table.add_row("Avg. Overall Confidence", f"{results.metrics['avg_overall_confidence_score']:.3f}")
            if "avg_roi_potential" in results.metrics:
                enhanced_metrics_table.add_row("Avg. ROI Potential", f"{results.metrics['avg_roi_potential']:.3f}")
            if "high_potential_leads" in results.metrics:
                enhanced_metrics_table.add_row("High Potential Leads", str(results.metrics['high_potential_leads']))

            # Calculate new aggregate metrics
            num_leads_with_contacts = sum(1 for r in results.results if r.get('contacts_emails_found', 0) > 0 or r.get('contacts_instagram_found', 0) > 0)
            if results.successful_leads > 0: # Avoid division by zero
                percent_leads_with_contacts = (num_leads_with_contacts / results.successful_leads) * 100
                enhanced_metrics_table.add_row("Leads with Contacts (%)", f"{percent_leads_with_contacts:.1f}%")
            else:
                enhanced_metrics_table.add_row("Leads with Contacts (%)", "N/A")

            avg_detailed_pain_points = sum(r.get('num_detailed_pain_points', 0) for r in results.results) / max(1, results.successful_leads)
            enhanced_metrics_table.add_row("Avg. Num. Detailed Pain Points", f"{avg_detailed_pain_points:.2f}")
            
            avg_value_props = sum(r.get('num_value_propositions', 0) for r in results.results) / max(1, results.successful_leads)
            enhanced_metrics_table.add_row("Avg. Num. Value Propositions", f"{avg_value_props:.2f}")

            qualification_counts = {}
            for result_item in results.results:
                tier = result_item.get("qualification_tier", "Unknown")
                qualification_counts[tier] = qualification_counts.get(tier, 0) + 1
            for tier, count in qualification_counts.items():
                enhanced_metrics_table.add_row(f"Leads in Tier '{tier}'", str(count))

            # Add content marketing aggregate metrics
            num_leads_with_content_ideas = sum(1 for r in results.results if r.get('content_marketing_generated'))
            if results.successful_leads > 0:
                percent_leads_with_content_ideas = (num_leads_with_content_ideas / results.successful_leads) * 100
                enhanced_metrics_table.add_row("Leads with Content Ideas (%)", f"{percent_leads_with_content_ideas:.1f}%")
            else:
                enhanced_metrics_table.add_row("Leads with Content Ideas (%)", "N/A")

            avg_blog_ideas = sum(r.get('content_marketing_num_blog_ideas', 0) for r in results.results if r.get('content_marketing_generated')) / max(1, num_leads_with_content_ideas) if num_leads_with_content_ideas > 0 else 0
            enhanced_metrics_table.add_row("Avg. Blog Ideas (if generated)", f"{avg_blog_ideas:.2f}")
            
            self.console.print(enhanced_metrics_table)

            self.console.print("\n✨ [bold magenta]Individual Lead Summaries (First 5 Processed):[/bold magenta]")
            for i, lead_item in enumerate(results.results):
                if i >= 5 :
                    self.console.print(f"... and {len(results.results) - 5} more successfully processed leads.")
                    break
                
                panel_content = (
                    f"[bold]URL:[/bold] {lead_item.get('url')}\n"
                    f"[bold]Overall Confidence:[/bold] {lead_item.get('overall_confidence_score', 'N/A'):.3f}\n"
                    f"[bold]Qualification Tier:[/bold] {lead_item.get('qualification_tier', 'N/A')} "
                    f"([italic]Justification:[/italic] {lead_item.get('qualification_justification', 'N/A')[:70]}...)\n"
                    f"[bold]Primary Pain Category:[/bold] {lead_item.get('primary_pain_category', 'N/A')} "
                    f"([italic]Urgency:[/italic] {lead_item.get('pain_urgency_level', 'N/A')}, [italic]Count:[/italic] {lead_item.get('num_detailed_pain_points', 0)})\n"
                    f"[bold]Recommended Strategy:[/bold] {lead_item.get('recommended_strategy_name', 'N/A')}\n"
                    f"  [italic]Hook:[/italic] {lead_item.get('recommended_strategy_hook', 'N/A')[:70]}...\n"
                    f"[bold]Detailed Plan Objective:[/bold] {lead_item.get('detailed_plan_main_objective', 'N/A')[:70]}...\n"
                    f"[bold]Message Channel:[/bold] {lead_item.get('message_channel', 'N/A')}\n"
                    f"[bold]Contacts - Emails:[/bold] {lead_item.get('contacts_emails_found', 0)} [bold]Insta:[/bold] {lead_item.get('contacts_instagram_found',0)}\n"
                    f"[bold]Tavily Enriched:[/bold] {'Yes' if lead_item.get('tavily_enriched') else 'No'}\n"
                    f"[bold]VPs:[/bold] {lead_item.get('num_value_propositions',0)} | "
                    f"[bold]Strat. Qs:[/bold] {lead_item.get('num_strategic_questions',0)} | "
                    f"[bold]Competitors:[/bold] {lead_item.get('num_competitors_identified',0)} | "
                    f"[bold]Triggers:[/bold] {lead_item.get('num_purchase_triggers',0)} | "
                    f"[bold]Objections:[/bold] {lead_item.get('num_objections_prepared',0)}\n"
                    f"[bold]Content Ideas Generated:[/bold] {'Yes' if lead_item.get('content_marketing_generated') else 'No'}"
                )
                if lead_item.get('content_marketing_generated'):
                    panel_content += (
                        f" (Blogs: {lead_item.get('content_marketing_num_blog_ideas', 0)}, "
                        f"Social: {lead_item.get('content_marketing_num_social_posts', 0)}, "
                        f"SEO: {lead_item.get('content_marketing_num_seo_keywords', 0)})\n"
                        f"  [italic]Sample Blog Title:[/italic] {lead_item.get('content_marketing_sample_blog_title', 'N/A')[:70]}...\n"
                        f"  [italic]Sample Social Post ({lead_item.get('content_marketing_sample_social_platform','N/A')}):[/italic] {lead_item.get('content_marketing_sample_social_text_preview', 'N/A')}"
                    )
                elif lead_item.get('content_marketing_error'):
                    panel_content += f" [italic](Error: {lead_item.get('content_marketing_error')[:50]}...)[/italic]"

                self.console.print(Panel(panel_content, title=f"Lead: {lead_item.get('company_name', 'N/A')}", border_style="blue", expand=True))
        
        elif results.mode == ProcessingMode.HYBRID: # Specific summary for hybrid
            # Could add more detailed comparison metrics here if needed
            self.console.print("[info]Hybrid mode executed both standard and enhanced pipelines.[/info]")
            # Potentially print top few lines of standard vs enhanced for same leads if data is structured that way
            # For now, the main process_leads for HYBRID combines results, so the above enhanced section would apply
            # if we ensure the results list has the enhanced data.
            # The current HYBRID mode in process_leads needs refinement to produce a single list of results
            # where each item indicates which pipeline it went through, for this report to be more effective.
            # For now, this section will be minimal for HYBRID.
            pass


    def save_results(self, results: ProcessingResults, output_file: str) -> None:
        output_data = {
            "processing_summary": {
                "mode": results.mode.value, "timestamp": datetime.now().isoformat(),
                "total_leads": results.total_leads, "successful_leads": results.successful_leads,
                "failed_leads": results.failed_leads, "processing_time": results.processing_time,
                "metrics": results.metrics
            },
            "configuration": {
                "product_service_context": self.product_service_context,
                "competitors_list": self.competitors_list,
                "tavily_enabled": hasattr(self, 'enhanced_processor') and bool(self.enhanced_processor.tavily_api_key if hasattr(self.enhanced_processor, 'tavily_api_key') else False) # Added hasattr
            },
            "results": results.results # This now contains the rich dictionaries from _enhanced_processing
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        self.console.print(f"✅ Results saved to: {output_file}")
    
    def _extract_company_name_from_analyzed(self, analyzed_lead: AnalyzedLead) -> str:
        site_data = analyzed_lead.validated_lead.site_data
        if site_data.google_search_data and site_data.google_search_data.title:
            title = site_data.google_search_data.title
            company_name = title.split(" - ")[0].split(" | ")[0].split(": ")[0]
            if len(company_name) > 5: return company_name.strip()
        url = str(site_data.url)
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        return domain.replace('www.', '').split('.')[0].title()

def load_harvester_data(file_path: str) -> HarvesterOutput:
    try:
        with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
        return HarvesterOutput(**data)
    except Exception as e:
        logger.error(f"Failed to load harvester data from {file_path}: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Enhanced Nellia Prospector - Multi-mode AI lead processing")
    parser.add_argument("harvester_file", help="Path to harvester output JSON file")
    parser.add_argument("-p", "--product", required=True, help="Product/service context for analysis")
    parser.add_argument("-m", "--mode", choices=[mode.value for mode in ProcessingMode], default=ProcessingMode.ENHANCED.value, help="Processing mode")
    parser.add_argument("-c", "--competitors", default="", help="Known competitors list")
    parser.add_argument("-n", "--limit", type=int, help="Limit number of leads to process")
    parser.add_argument("-o", "--output", help="Output file path (default: auto-generated)")
    parser.add_argument("-l", "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Logging level")
    args = parser.parse_args()
    
    logger.remove()
    logger.add(sys.stderr, level=args.log_level)
    
    try:
        harvester_data = load_harvester_data(args.harvester_file)
        processor = EnhancedNelliaProspector(
            product_service_context=args.product, competitors_list=args.competitors,
            processing_mode=ProcessingMode(args.mode), tavily_api_key=os.getenv("TAVILY_API_KEY")
        )
        results = processor.process_leads(harvester_data, args.limit)
        processor.generate_report(results)
        if args.output: output_file = args.output
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"enhanced_prospector_results_{args.mode}_{timestamp}.json"
        processor.save_results(results, output_file)
        
        if results.mode == ProcessingMode.ENHANCED and results.successful_leads > 0:
            avg_confidence = results.metrics.get("avg_overall_confidence_score", results.metrics.get("avg_confidence_score",0))
            avg_roi_potential = results.metrics.get("avg_roi_potential", 0)
            high_potential_count = results.metrics.get("high_potential_leads", 0)
            rprint(Panel(
                f"🎯 ROI OPTIMIZATION SUMMARY\n\n"
                f"Target: 527% ROI Achievement\n" # Placeholder value
                f"High Potential Leads: {high_potential_count}/{results.successful_leads}\n"
                f"Avg Overall Confidence Score: {avg_confidence:.3f}\n"
                f"Avg ROI Potential: {avg_roi_potential:.3f}\n"
                f"Brazilian Market Optimization: ENABLED\n\n" # Placeholder
                f"✨ Ready for high-converting outreach!",
                title="Enhanced Processing Complete", border_style="gold1"
            ))
    except KeyboardInterrupt: logger.info("Processing interrupted by user"); sys.exit(1)
    except Exception as e: logger.error(f"Processing failed: {e}\n{traceback.format_exc()}"); sys.exit(1)

if __name__ == "__main__":
    main()
