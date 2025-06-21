"""
Approach Strategy Agent for Nellia Prospector
Develops strategic approach plans for leads with personas.
"""

from typing import Optional, Dict, List, Any # Added Dict, List
from datetime import datetime
from loguru import logger
import json

from data_models.lead_structures import (
    LeadWithPersona, 
    LeadWithStrategy, 
    ApproachStrategy,
    CommunicationChannel
)
from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

class ApproachStrategyAgent(BaseAgent[LeadWithPersona, LeadWithStrategy]):
    """Agent responsible for creating strategic approach plans for leads"""
    
    def __init__(self, llm_client: Optional[LLMClientBase] = None, product_service_context: str = "", output_language: str = "en-US"):
        super().__init__(
            name="ApproachStrategyAgent",
            description="Develops strategic approach plans for leads with personas",
            llm_client=llm_client,
            config={"product_service_context": product_service_context, "output_language": output_language}
        )
        self.product_service_context = product_service_context
        self.output_language = output_language
    
    def process(self, lead_with_persona: LeadWithPersona) -> LeadWithStrategy:
        """
        Create a strategic approach plan for the lead with persona
        
        Args:
            lead_with_persona: LeadWithPersona with company analysis and persona
            
        Returns:
            LeadWithStrategy with complete approach strategy
        """
        logger.info(f"Creating strategy for: {lead_with_persona.analyzed_lead.validated_lead.site_data.url}")
        
        # Build the prompt for strategy creation
        prompt = self._build_strategy_prompt(lead_with_persona, self.output_language)
        
        # Generate LLM response
        response_text = self.generate_llm_response(prompt, output_language=self.output_language)
        
        # Parse the response
        strategy_data = self.parse_llm_json_response(response_text, None)
        
        # Create ApproachStrategy from parsed data
        strategy = self._create_approach_strategy(strategy_data)
        
        # Build and return result
        result = LeadWithStrategy(
            lead_with_persona=lead_with_persona,
            strategy=strategy,
            strategy_timestamp=datetime.now()
        )
        
        logger.info(f"Strategy created: {strategy.primary_channel.value if strategy.primary_channel else 'N/A'} approach for {strategy.first_interaction_goal}")
        return result
    
    def _build_strategy_prompt(self, lead_with_persona: LeadWithPersona, output_language: str) -> str:
        """Build the prompt for strategy creation, now in English and language-aware."""
        
        analyzed_lead = lead_with_persona.analyzed_lead
        persona = lead_with_persona.persona
        
        # Extract Brazilian business culture context (now in English)
        market_context_str = self._get_brazilian_business_context(analyzed_lead.analysis.company_sector or "General")
        
        # Ensure product_service_context has a default if empty for the prompt
        product_context_for_prompt = self.product_service_context or "our AI solutions for sales process optimization and B2B lead generation"

        # Constructing context strings carefully to avoid issues with None or empty lists
        company_services_str = ', '.join(analyzed_lead.analysis.main_services) if analyzed_lead.analysis.main_services else "Not detailed in initial analysis."
        company_challenges_str = ', '.join(analyzed_lead.analysis.potential_challenges) if analyzed_lead.analysis.potential_challenges else "Not detailed in initial analysis."

        persona_responsibilities_str = ', '.join(persona.key_responsibilities) if persona.key_responsibilities else "Not detailed."
        persona_goals_str = ', '.join(persona.professional_goals) if persona.professional_goals else "Not detailed."
        persona_challenges_str = ', '.join(persona.main_challenges) if persona.main_challenges else "Not detailed."
        persona_motivations_str = ', '.join(persona.motivations) if persona.motivations else "Not detailed."

        return f"""You are a Senior B2B Sales Strategist, highly experienced and specialized in the target market (e.g., Brazilian market, adapt as needed based on context).
Your mission is to develop a personalized and effective approach plan for the decision-maker described below, aiming to maximize conversion potential and achieve high-impact results (e.g., significant ROI).

AVAILABLE INFORMATION:

1. TARGET COMPANY CONTEXT:
   - URL: {analyzed_lead.validated_lead.site_data.url}
   - Industry Sector: {analyzed_lead.analysis.company_sector or 'Not Specified'}
   - Estimated Size: {analyzed_lead.analysis.company_size_estimate or 'Not Determined'}
   - Main Services/Products: {company_services_str}
   - Identified Potential Challenges: {company_challenges_str}
   - Inferred Culture and Values: {analyzed_lead.analysis.company_culture_values or 'Could not determine'}
   - General Company Diagnosis: {analyzed_lead.analysis.general_diagnosis or 'Not available'}

2. PERSONA CONTEXT (Decision-Maker):
   - Fictional Name (for reference): {persona.fictional_name or 'N/A'}
   - Likely Role: {persona.likely_role or 'Not Specified'}
   - Key Responsibilities: {persona_responsibilities_str}
   - Professional Goals: {persona_goals_str}
   - Main Professional Challenges: {persona_challenges_str}
   - Motivation Factors: {persona_motivations_str}
   - Preferred Communication Style: {persona.communication_style or 'Not Specified'}
   - Inferred Decision-Making Process: {persona.decision_making_process or 'Not Specified'}

3. OUR PRODUCT/SERVICE:
   "{product_context_for_prompt}"

4. TARGET MARKET CONTEXT (e.g., Brazilian market, for the target company's sector):
{market_context_str}

INSTRUCTIONS FOR THE APPROACH STRATEGY:
Based on ALL the information provided, develop a strategic and detailed approach plan.
The plan should be practical, actionable, and culturally adapted to the target market (e.g., Brazil).
Connect the specific needs of the persona and the company's challenges directly to the benefits of our product/service.
The focus is on creating value, building relationships, and facilitating a favorable purchase decision.

RESPONSE FORMAT:
Respond EXCLUSIVELY with a valid JSON object, following the schema and field descriptions below.
DO NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.

EXPECTED JSON SCHEMA:
{{
    "primary_channel": "string - The MOST recommended communication channel for the first contact. Choose from: 'email', 'linkedin', 'whatsapp', 'phone'.",
    "secondary_channel": "string | null - An alternative or follow-up channel, if appropriate. Choose from: 'email', 'linkedin', 'whatsapp', 'phone', or use null if no clear secondary.",
    "tone_of_voice": "string - Describe the recommended tone of voice (e.g., 'Consultative and educational, focused on partnership', 'Formal, direct, and respectful of hierarchy', 'Friendly, collaborative, and innovative'). Consider the persona and market context.",
    "key_value_propositions": ["string", ...] - List of 2-3 KEY and concise value propositions, highlighting how our product/service solves the persona/company challenges or helps achieve their goals. E.g., 'Reduce operational costs by X% through Y', 'Increase sales team efficiency with Z'.",
    "talking_points": ["string", ...] - List of 2-3 main talking points to use in the initial interaction, derived from value propositions but phrased more conversationally.",
    "potential_objections": {{ "string": "string", ... }} - Dictionary where keys are common anticipated objections (e.g., 'We already have a solution', 'We don't have a budget now', 'This is not a priority') and values are consultative and effective responses, focused on better understanding and adding value, rather than being defensive.",
    "opening_questions": ["string", ...] - List of 1-2 open-ended, insightful, and context-specific questions for the lead, to start the conversation, demonstrate research, and discover more about their current needs.",
    "first_interaction_goal": "string - The main, specific, and measurable objective of the first contact (e.g., 'Schedule a 15-minute diagnostic call to explore [specific challenge]', 'Obtain confirmation that [challenge X] is relevant and understand its current impact', 'Present a similar success case and gather initial feedback').",
    "follow_up_strategy": "string - Describe a concise and logical follow-up strategy, with 2-3 steps, if the first contact does not achieve the expected result (e.g., '1. Send a relevant article/case study via LinkedIn after 3 days, mentioning a point from the initial conversation. 2. If no response, try a brief phone call after 1 week to offer help on a specific challenge. 3. Invite to a relevant webinar if previous steps do not progress.')."
}}

FINAL REMINDERS:
- Fill ALL JSON fields according to the schema.
- For list fields (arrays), if no specific information is generated, return an empty list `[]`.
- For `secondary_channel`, if not applicable, use `null`.
- Base ALL strategy strictly on the information provided. Do not invent details not present in the context.
- The quality and personalization of the strategy are crucial.

Important: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is.
"""
    
    def _get_brazilian_business_context(self, sector: Optional[str]) -> str:
        """Get target market (e.g., Brazilian) business context based on sector, now in English."""
        sector_lower = (sector or "").lower()

        context_map = { # Keywords for sectors should ideally be in English if sectors in analysis are English
            "technology": """- Technology Sector: Decision-makers may be technical and value concrete data, clear ROI, and innovation. Communication can be more direct. LinkedIn is widely used. Success cases and demos are effective.""",
            "services": """- Services Sector: Personal relationships and trust are fundamental. Consultative and less aggressive communication. Networking and referrals are highly valued. Decision-making process can be collaborative and longer.""",
            "industry": """- Industrial Sector: Tends to be more conservative, focused on tangible ROI, efficiency, and reliability. Hierarchy can be important. Success cases and technical knowledge of the sector are differentiators."""
            # Add more sectors and their specific contexts as needed
        }
        
        specific_context = ""
        for key, context_text in context_map.items():
            if key in sector_lower: # Match against English keywords
                specific_context = context_text
                break

        # General context, adaptable for different markets but initially framed for Brazil
        general_market_context = """- General Market Context (e.g., Brazil): Relationships often precede business; invest in personal connection (even virtually). Communication tends to be more indirect and cordial than in some other cultures; avoid being overly direct or transactional in the first contact. Demonstrate genuine knowledge and interest in the lead's market and company. Flexibility and patience may be necessary."""

        return f"{specific_context}\n{general_market_context}".strip()
    
    def _create_approach_strategy(self, strategy_data: Optional[Dict[str, Any]]) -> ApproachStrategy:
        """Create ApproachStrategy from parsed JSON data, with English fallbacks."""
        
        if not strategy_data:
            logger.warning("Strategy data is None, returning fallback strategy.")
            strategy_data = {}

        try:
            primary_channel_str = strategy_data.get('primary_channel', 'email')
            primary_channel = self._map_channel(primary_channel_str)
            
            secondary_channel_str = strategy_data.get('secondary_channel')
            secondary_channel = None
            if secondary_channel_str and secondary_channel_str.lower() != 'null': # Check for 'null' string
                secondary_channel = self._map_channel(secondary_channel_str)
            
            key_value_propositions = strategy_data.get('key_value_propositions', [])
            if not isinstance(key_value_propositions, list): key_value_propositions = ['Default value proposition due to parsing error']

            talking_points = strategy_data.get('talking_points', [])
            if not isinstance(talking_points, list): talking_points = ['Default talking point due to parsing error']

            potential_objections = strategy_data.get('potential_objections', {})
            if not isinstance(potential_objections, dict): potential_objections = {'default_objection': 'Default response due to parsing error'}

            opening_questions = strategy_data.get('opening_questions', [])
            if not isinstance(opening_questions, list): opening_questions = ['Default question due to parsing error']


            return ApproachStrategy(
                primary_channel=primary_channel,
                secondary_channel=secondary_channel,
                tone_of_voice=strategy_data.get('tone_of_voice', 'Professional and consultative'),
                key_value_propositions=key_value_propositions,
                talking_points=talking_points,
                potential_objections=potential_objections,
                opening_questions=opening_questions,
                first_interaction_goal=strategy_data.get('first_interaction_goal', 'Spark interest and understand needs'),
                follow_up_strategy=strategy_data.get('follow_up_strategy', 'Educational follow-up in 3-5 business days')
            )
            
        except Exception as e: # pylint: disable=broad-except
            logger.warning(f"Failed to create strategy from data due to: {e}. Data: {strategy_data}")
            # Return fallback strategy with English defaults
            return ApproachStrategy(
                primary_channel=CommunicationChannel.EMAIL,
                secondary_channel=CommunicationChannel.LINKEDIN,
                tone_of_voice="Professional and consultative (fallback)",
                key_value_propositions=[
                    "Sales process optimization (fallback)",
                    "ROI increase (fallback)",
                    "Personalized approach (fallback)"
                ],
                talking_points=[
                    "Success cases in the target market (fallback)",
                    "Integration with existing processes (fallback)",
                    "Specialized support (fallback)"
                ],
                potential_objections={
                    "cost": "I understand budget concerns. Can we explore options that fit or demonstrate the ROI that justifies the investment? (fallback)",
                    "satisfied_with_current_solution": "That's great you already have a solution! What aspects do you value most in it, and is there anything that could be even better? (fallback)"
                },
                opening_questions=[
                    "What are your biggest challenges currently in the area of [related to product/service]? (fallback)",
                    "How does your team measure success regarding [objective product/service addresses]? (fallback)"
                ],
                first_interaction_goal="Establish initial contact and assess initial interest (fallback)",
                follow_up_strategy="Send supporting material and schedule a conversation if there's interest (fallback)"
            )
    
    def _map_channel(self, channel_str: Optional[str]) -> CommunicationChannel:
        """Map string to CommunicationChannel enum"""
        channel_mapping = {
            'email': CommunicationChannel.EMAIL,
            'linkedin': CommunicationChannel.LINKEDIN,
            'whatsapp': CommunicationChannel.WHATSAPP,
            'phone': CommunicationChannel.PHONE
        }
        return channel_mapping.get((channel_str or "").lower(), CommunicationChannel.EMAIL) # Default to EMAIL if None or invalid
