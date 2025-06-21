"""
Message Crafting Agent for Nellia Prospector
Creates personalized outreach messages based on strategy and persona.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
import json
import re

from data_models.lead_structures import (
    LeadWithStrategy,
    FinalProspectPackage,
    PersonalizedMessage,
    CommunicationChannel
)
from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

class MessageCraftingAgent(BaseAgent[LeadWithStrategy, FinalProspectPackage]):
    """Agent responsible for creating personalized outreach messages"""
    
    def __init__(self, llm_client: Optional[LLMClientBase] = None, output_language: str = "en-US", **kwargs):
        super().__init__(
            name="MessageCraftingAgent",
            description="Creates personalized outreach messages for B2B leads",
            llm_client=llm_client,
            **kwargs
        )
        self.output_language = output_language
    
    def process(self, lead_with_strategy: LeadWithStrategy) -> FinalProspectPackage:
        """
        Create personalized outreach message for the lead with strategy
        
        Args:
            lead_with_strategy: LeadWithStrategy with complete approach plan
            
        Returns:
            FinalProspectPackage with ready-to-send message
        """
        lead_url = str(lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.site_data.url)
        logger.info(f"✍️ MESSAGE CRAFTING AGENT STARTING for: {lead_url}")
        
        # Build the prompt for message creation
        prompt = self._build_message_prompt(lead_with_strategy, self.output_language)
        
        # Generate LLM response
        llm_response_obj = self.generate_llm_response(prompt, output_language=self.output_language)

        llm_response_str = llm_response_obj.content if llm_response_obj else None

        # Parse the response
        message_data_dict = self.parse_llm_json_response(llm_response_str, dict) if llm_response_str else None
        
        # Create PersonalizedMessage from parsed data
        # Pass the determined primary_channel to _create_personalized_message
        message = self._create_personalized_message(message_data_dict, lead_with_strategy.strategy.primary_channel)
        
        # Build final result
        result = FinalProspectPackage(
            lead_with_strategy=lead_with_strategy,
            personalized_message=message,
            processing_complete_timestamp=datetime.now(),
            lead_id=self._generate_lead_id(lead_url),
            confidence_score=self._calculate_confidence_score(lead_with_strategy, message) # Pass message for score calc
        )
        
        logger.info(f"✅ Message created for {lead_url}: Channel: {message.channel.value if message.channel else 'N/A'}, CTA: {message.call_to_action[:50]}...")
        return result
    
    def _build_message_prompt(self, lead_with_strategy: LeadWithStrategy, output_language: str) -> str:
        """Build the prompt for message creation, now in English and language-aware."""
        
        analyzed_lead = lead_with_strategy.lead_with_persona.analyzed_lead
        persona = lead_with_strategy.lead_with_persona.persona
        strategy = lead_with_strategy.strategy
        
        company_name = self._extract_company_name(lead_with_strategy)
        channel_guidance = self._get_channel_guidance(strategy.primary_channel, output_language) # Pass language
        
        # Helper for joining lists or providing 'N/A'
        def join_list_or_na(lst: Optional[List[str]]) -> str:
            return ', '.join(lst) if lst and len(lst) > 0 else 'N/A'

        # Prompt template in English
        return f"""You are a Senior Strategic B2B Copywriter, specializing in creating highly personalized and effective first-contact messages, with deep knowledge of the target market (e.g., Brazilian market) and its cultural nuances.
Your task is to create a message that generates genuine engagement, builds rapport, and motivates a positive response, advancing the conversation to the next stage defined in the contact objective.

MAIN MESSAGE OBJECTIVE: Contribute to ROI growth through an approach of maximum personalization and contextual relevance.

COMPLETE LEAD AND STRATEGY CONTEXT (provided by the strategy team):

1.  TARGET COMPANY:
    - Name: {company_name}
    - URL: {analyzed_lead.validated_lead.site_data.url}
    - Sector: {analyzed_lead.analysis.company_sector or 'N/A'}
    - Target Company's Main Services/Products: {join_list_or_na(analyzed_lead.analysis.main_services)}
    - Target Company's Identified Challenges: {join_list_or_na(analyzed_lead.analysis.potential_challenges)}
    - Perceived Opportunity for Us: {analyzed_lead.analysis.opportunity_fit or 'N/A'}

2.  PERSONA (Decision-Maker at Target Company):
    - Fictional Name: {persona.fictional_name or 'N/A'} ({persona.likely_role or 'Role not specified'})
    - Key Professional Goals: {join_list_or_na(persona.professional_goals)}
    - Main Challenges: {join_list_or_na(persona.main_challenges)}
    - Preferred Communication Style: {persona.communication_style or 'Not specified'}
    - How They Seek Solutions: {persona.solution_seeking or 'Not specified'}

3.  DEFINED APPROACH STRATEGY:
    - Selected Primary Channel: {strategy.primary_channel.value}
    - Recommended Tone of Voice: {strategy.tone_of_voice}
    - Key Value Propositions for this Lead: {join_list_or_na(strategy.key_value_propositions)}
    - Main Talking Points: {join_list_or_na(strategy.talking_points)}
    - Suggested Opening Questions: {join_list_or_na(strategy.opening_questions)}
    - Specific Objective of this First Contact: {strategy.first_interaction_goal}

4.  OUR PRODUCT/SERVICE (that we are offering):
    "{analyzed_lead.product_service_context or 'Our innovative solution'}"

5.  SPECIFIC GUIDELINES FOR THE '{strategy.primary_channel.value}' CHANNEL:
{channel_guidance}

CRITICAL INSTRUCTIONS FOR THE MESSAGE:
1.  **Ultra-Personalization:** The message MUST be perceived as unique to {company_name} and {persona.fictional_name}. Reference specific information from the provided context.
2.  **Demonstrate Research:** Show that you understand the company's and persona's challenges and objectives.
3.  **Direct Value Connection:** CLEARLY connect the benefits of OUR PRODUCT/SERVICE to the identified challenges/objectives. Use the "Key Value Propositions".
4.  **Tone of Voice and Style:** STRICTLY follow the "Recommended Tone of Voice" and channel guidelines.
5.  **Call to Action (CTA):** The CTA must be clear, low-friction, and aligned with the "Specific Objective of this First Contact".
6.  **Concise and Impactful:** Respect channel limits and nature. Get to the point, but with impact.
7.  **Authenticity:** The message should sound genuine and human, focused on helping, not just selling.
8.  **Market Context:** Adapt language and approach for the target market (e.g., Brazilian market), valuing relationships.
9.  **Initial Hook:** Use or adapt one of the "Suggested Opening Questions" or create a strong, relevant initial hook.
10. **Avoid Clichés:** Do not use phrases like "Hope you are well" or excessive jargon.

RESPONSE FORMAT:
Respond EXCLUSIVELY with a valid JSON object, following the schema and field descriptions below. Do NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.

EXPECTED JSON SCHEMA:
{{
    "subject_line": "string | null - Message subject. REQUIRED for 'Email' channel (max 50-60 characters, concise and intriguing). For other channels (LinkedIn, WhatsApp), MUST be null.",
    "message_body": "string - The complete personalized message body, following all instructions and adapted for the '{strategy.primary_channel.value}' channel.",
    "call_to_action": "string - The specific and clear call-to-action used in the message, aligned with the 'Specific Objective of this First Contact'.",
    "personalization_elements_used": ["string", ...] - List of the main personalization elements you incorporated into the message (e.g., 'Company name', 'Specific persona challenge X', 'Recent company news Y', 'Reference to persona objective Z'). Minimum of 2, maximum of 5. If specific elements cannot be identified, return an empty list [].",
    "estimated_read_time_seconds": "integer - An estimate of the message's read time in seconds (e.g., for a 100-word body, approximately 30-40 seconds). Must always be an integer."
}}

Important: Generate your entire response, including all textual content and string values within any JSON structure, strictly in the following language: {output_language}. Do not include any English text unless it is part of the original input data that should be preserved as is.
"""
    
    def _get_channel_guidance(self, channel: Optional[CommunicationChannel], output_language: str) -> str: # Added output_language
        """Get channel-specific guidance for message creation, now in English."""
        
        # Default guidance if channel is None
        if channel is None:
            return """
GENERAL GUIDELINES (Channel not specified):
- Maintain professional yet approachable tone.
- Focus on value for the recipient.
- Clear, low-commitment CTA.
- Demonstrate research and personalization."""

        if channel == CommunicationChannel.EMAIL:
            return """
EMAIL GUIDELINES:
- Subject: Specific, intriguing, no spam words (max 50-60 characters).
- Suggested Structure: Personalized greeting -> Connection/Context (show research) -> Clear and concise Value Proposition linked to pain/objective -> Low-friction CTA -> Professional signature.
- Ideal Length: 80-150 words.
- Format: Professional, short paragraphs, good use of line breaks.
- CTA: Specific and low-commitment (e.g., "Available for a quick 10-15 minute chat?", "Would you like me to share a relevant case study?")."""
            
        elif channel == CommunicationChannel.LINKEDIN:
            return """
LINKEDIN GUIDELINES (Direct Message or Connection Note):
- Subject: Not applicable for DMs. For connection notes, be brief and relevant.
- Suggested Structure: Greeting -> Relevant connection point (e.g., profile, article, mutual connection) -> Brief value proposition -> Engaging question or soft CTA.
- Ideal Length: 50-100 words (connection notes are shorter).
- Format: Conversational, yet professional. Avoid excessive formality.
- CTA: Invitation to connect (if a note), or an open-ended question to start dialogue, or suggest a useful resource. Avoid aggressive immediate sales CTAs."""
            
        elif channel == CommunicationChannel.WHATSAPP:
            return """
WHATSAPP GUIDELINES (use with extreme caution and only if indicated as an acceptable channel):
- Subject: Not applicable.
- Suggested Structure: Brief greeting and identification -> Concise reason for contact (with high value and personalization) -> Very light CTA (e.g., "Can I send a quick audio explaining better?", "Would a link about X be useful?").
- Ideal Length: 2-4 short, direct sentences. Extremely concise.
- Format: Informal, but professional. Use emojis sparingly and only if aligned with persona's tone.
- CTA: Focused on getting permission to continue the conversation or send more information. Avoid asking for long meetings. Prioritize respect for time and personal channel."""
            
        else:
            return """
GENERAL GUIDELINES:
- Maintain professional yet approachable tone.
- Focus on value for the recipient.
- Clear, low-commitment CTA.
- Demonstrate research and personalization."""
    
    def _create_personalized_message(self, message_data_dict: Optional[Dict[str, Any]], channel: Optional[CommunicationChannel]) -> PersonalizedMessage:
        """Create PersonalizedMessage from parsed JSON data, with English fallbacks."""

        effective_channel = channel if channel is not None else CommunicationChannel.EMAIL

        if not message_data_dict:
            self.logger.warning(f"Message data is None, returning fallback message for channel {effective_channel.value}.")
            return self._create_fallback_message(effective_channel)

        try:
            subject_line = message_data_dict.get('subject_line')
            if effective_channel != CommunicationChannel.EMAIL and subject_line is not None:
                self.logger.warning(f"LLM provided subject_line for non-Email channel ({effective_channel.value}). Setting to None.")
                subject_line = None
            
            personalization_elements = message_data_dict.get('personalization_elements', [])
            if not isinstance(personalization_elements, list):
                personalization_elements = [str(personalization_elements)] if personalization_elements else []


            return PersonalizedMessage(
                channel=effective_channel,
                subject_line=subject_line,
                message_body=message_data_dict.get('message_body', 'Message not available due to parsing error.'), # English
                call_to_action=message_data_dict.get('call_to_action', 'Would you like to explore how we can help?'), # English
                personalization_elements=personalization_elements,
                estimated_read_time=int(message_data_dict.get('estimated_read_time_seconds', 60)),
                ab_variant=None
            )
            
        except Exception as e: # pylint: disable=broad-except
            self.logger.warning(f"Failed to create PersonalizedMessage from data: {e}. Data: {message_data_dict}")
            return self._create_fallback_message(effective_channel)
    
    def _create_fallback_message(self, channel: CommunicationChannel) -> PersonalizedMessage:
        """Create a fallback message when parsing fails, now in English."""
        self.logger.warning(f"Creating fallback message for channel: {channel.value}")
        
        if channel == CommunicationChannel.EMAIL:
            return PersonalizedMessage(
                channel=channel,
                subject_line="Optimization and Growth Opportunity (fallback)",
                message_body="""Hello,\n\nWe have reviewed your company's profile and identified potential synergies with our solutions.\n\nWe believe we can assist in process optimization and drive results.\n\nWould you be open to a brief conversation to explore this?\n\nSincerely,\nProspecting Team (fallback)""",
                call_to_action="Schedule a 15-minute conversation.",
                personalization_elements=["Company sector (fallback)"],
                estimated_read_time=45
            )
        return PersonalizedMessage(
            channel=channel,
            subject_line=None,
            message_body="""Hello! We've identified that your company could benefit from our process optimization solutions. I believe a brief conversation would be very productive. What is your availability?""",
            call_to_action="Schedule a brief conversation.",
            personalization_elements=["Company sector (fallback)"],
            estimated_read_time=30
        )
    
    def _extract_company_name(self, lead_with_strategy: LeadWithStrategy) -> str:
        """Extract company name from various potential locations in the input."""
        # Prefer company_name if directly available (e.g., from a future enriched field)
        # For now, using existing logic based on AnalyzedLead
        analyzed_lead = lead_with_strategy.lead_with_persona.analyzed_lead

        # Try from explicit company_name field if it existed in LeadAnalysis (it doesn't directly)
        # For now, we rely on parsing from URL or Google Search title

        site_data = analyzed_lead.validated_lead.site_data
        if site_data.google_search_data and site_data.google_search_data.title:
            title = site_data.google_search_data.title
            company_name = title.split(" - ")[0].split(" | ")[0].split(": ")[0]
            company_name = re.sub(r'\s*\([^)]*\)', '', company_name)
            if len(company_name) > 3 and not any(char in company_name.lower() for char in ['http', 'www', '.com']): # Slightly more lenient length
                return company_name.strip()
        
        url = str(site_data.url)
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        domain = domain.replace('www.', '')
        # More robustly split by '.' and title case parts, e.g. "mycompany.com" -> "Mycompany"
        return domain.split('.')[0].title()
    
    def _generate_lead_id(self, url: str) -> str:
        """Generate a unique lead ID"""
        import hashlib
        return hashlib.md5(f"{url}_{datetime.now().isoformat()}".encode()).hexdigest()[:12] # Slightly longer ID
    
    def _calculate_confidence_score(self, lead_with_strategy: LeadWithStrategy, message: PersonalizedMessage) -> float:
        """Calculate confidence score based on data quality and message generation success"""
        
        score = 0.0
        
        # Base score from relevance
        relevance = lead_with_strategy.lead_with_persona.analyzed_lead.analysis.relevance_score or 0.0
        score += relevance * 0.3 # Max 0.3
        
        # Extraction success bonus
        if lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.extraction_successful:
            score += 0.15
        
        # Persona detail
        persona = lead_with_strategy.lead_with_persona.persona
        if persona.key_responsibilities and len(persona.key_responsibilities) > 0: score += 0.1
        if persona.main_challenges and len(persona.main_challenges) > 0 : score += 0.1

        # Strategy detail
        strategy = lead_with_strategy.strategy
        if strategy.key_value_propositions and len(strategy.key_value_propositions) > 0: score += 0.1
        if strategy.talking_points and len(strategy.talking_points) > 0 : score += 0.05
        if strategy.opening_questions and len(strategy.opening_questions) > 0: score += 0.05

        # Message generation success
        if message.message_body and message.message_body != 'Message not available due to parsing error.' and message.message_body != self._create_fallback_message(message.channel).message_body:
            score += 0.15

        return min(round(score, 2), 1.0)

