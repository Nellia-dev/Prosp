"""
Message Crafting Agent for Nellia Prospector
Creates personalized outreach messages based on strategy and persona.
"""

from typing import List, Optional
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
from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClient


class MessageCraftingAgent(BaseAgent):
    """Agent responsible for creating personalized outreach messages"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(agent_name="MessageCraftingAgent")
        self.llm_client = llm_client or LLMClient()
    
    def execute(self, lead_with_strategy: LeadWithStrategy) -> FinalProspectPackage:
        """
        Create personalized outreach message for the lead with strategy
        
        Args:
            lead_with_strategy: LeadWithStrategy with complete approach plan
            
        Returns:
            FinalProspectPackage with ready-to-send message
        """
        self.start_execution()
        
        try:
            lead_url = str(lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.site_data.url)
            logger.info(f"Creating message for lead: {lead_url}")
            
            # Create personalized message using LLM
            message = self._create_message(lead_with_strategy)
            
            # Build final result
            result = FinalProspectPackage(
                lead_with_strategy=lead_with_strategy,
                personalized_message=message,
                processing_complete_timestamp=datetime.now(),
                lead_id=self._generate_lead_id(lead_url),
                confidence_score=self._calculate_confidence_score(lead_with_strategy)
            )
            
            self.end_execution(success=True)
            logger.info(f"Message created: {message.channel.value} message with CTA: {message.call_to_action[:50]}...")
            
            return result
            
        except Exception as e:
            self.end_execution(success=False, error=str(e))
            logger.error(f"Error creating message: {e}")
            raise
    
    def _create_message(self, lead_with_strategy: LeadWithStrategy) -> PersonalizedMessage:
        """Create personalized message using LLM analysis"""
        
        # Prepare context for LLM
        message_context = {
            "url": str(lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.site_data.url),
            "company_name": self._extract_company_name(lead_with_strategy),
            "company_sector": lead_with_strategy.lead_with_persona.analyzed_lead.analysis.company_sector,
            "main_services": lead_with_strategy.lead_with_persona.analyzed_lead.analysis.main_services,
            "challenges": lead_with_strategy.lead_with_persona.analyzed_lead.analysis.potential_challenges,
            "opportunity_fit": lead_with_strategy.lead_with_persona.analyzed_lead.analysis.opportunity_fit,
            "persona_name": lead_with_strategy.lead_with_persona.persona.fictional_name,
            "persona_role": lead_with_strategy.lead_with_persona.persona.likely_role,
            "persona_goals": lead_with_strategy.lead_with_persona.persona.professional_goals,
            "persona_challenges": lead_with_strategy.lead_with_persona.persona.main_challenges,
            "communication_style": lead_with_strategy.lead_with_persona.persona.communication_style,
            "channel": lead_with_strategy.strategy.primary_channel,
            "tone_of_voice": lead_with_strategy.strategy.tone_of_voice,
            "value_propositions": lead_with_strategy.strategy.key_value_propositions,
            "talking_points": lead_with_strategy.strategy.talking_points,
            "opening_questions": lead_with_strategy.strategy.opening_questions,
            "first_interaction_goal": lead_with_strategy.strategy.first_interaction_goal,
            "product_service": lead_with_strategy.lead_with_persona.analyzed_lead.product_service_context
        }
        
        prompt = self._build_message_prompt(message_context)
        
        # Get LLM response
        response = self.llm_client.generate_text(prompt)
        
        # Parse response into PersonalizedMessage
        return self._parse_message_response(response, lead_with_strategy.strategy.primary_channel)
    
    def _build_message_prompt(self, context: dict) -> str:
        """Build the prompt for message creation"""
        
        channel_guidance = self._get_channel_guidance(context['channel'])
        
        return f"""
Você é um Redator de Copywriting B2B Sênior especializado em mensagens de primeiro contato.
Sua tarefa é criar uma mensagem altamente personalizada e persuasiva para gerar uma resposta positiva.

CONTEXTO DA EMPRESA:
- Nome: {context['company_name']}
- URL: {context['url']}
- Setor: {context['company_sector']}
- Principais serviços: {', '.join(context['main_services'])}
- Desafios identificados: {', '.join(context['challenges'])}
- Oportunidade identificada: {context['opportunity_fit']}

CONTEXTO DA PERSONA:
- Nome fictício: {context['persona_name']} ({context['persona_role']})
- Objetivos: {', '.join(context['persona_goals'])}
- Desafios: {', '.join(context['persona_challenges'])}
- Estilo de comunicação: {context['communication_style']}

ESTRATÉGIA DE ABORDAGEM:
- Canal: {context['channel'].value}
- Tom de voz: {context['tone_of_voice']}
- Propostas de valor: {', '.join(context['value_propositions'])}
- Pontos principais: {', '.join(context['talking_points'])}
- Perguntas de abertura: {', '.join(context['opening_questions'])}
- Objetivo: {context['first_interaction_goal']}

PRODUTO/SERVIÇO:
{context['product_service']}

{channel_guidance}

INSTRUÇÕES:
Crie uma mensagem de contato inicial que seja:
1. Altamente personalizada para {context['company_name']} e {context['persona_name']}
2. Demonstre que você pesquisou sobre a empresa
3. Foque nos benefícios específicos para os desafios identificados
4. Use o tom de voz apropriado: {context['tone_of_voice']}
5. Tenha um CTA claro e específico
6. Seja concisa mas impactante
7. Evite jargões excessivos e seja autêntica

Responda no formato JSON:
{{
    "subject_line": "Assunto da mensagem (se aplicável para o canal)",
    "message_body": "Corpo completo da mensagem",
    "call_to_action": "Call-to-action específico",
    "personalization_elements": ["elemento1", "elemento2", "elemento3"],
    "estimated_read_time": 30
}}

Responda APENAS com o JSON válido, sem explicações adicionais.
"""
    
    def _get_channel_guidance(self, channel: CommunicationChannel) -> str:
        """Get channel-specific guidance for message creation"""
        
        if channel == CommunicationChannel.EMAIL:
            return """
DIRETRIZES PARA E-MAIL:
- Assunto: Curto, específico e intrigante (máx 50 caracteres)
- Estrutura: Saudação personalizada → Conexão/Pesquisa → Valor → CTA → Assinatura
- Tamanho: 100-150 palavras idealmente
- Formato: Profissional mas não formal demais
- CTA: Específico (ex: "15 minutos na próxima semana")
"""
        elif channel == CommunicationChannel.LINKEDIN:
            return """
DIRETRIZES PARA LINKEDIN:
- Sem assunto (conexão ou mensagem direta)
- Estrutura: Conexão pessoal → Valor rápido → Pergunta/CTA
- Tamanho: 50-100 palavras (LinkedIn limita mensagens)
- Formato: Conversacional e profissional
- CTA: Convite para conexão ou conversa breve
"""
        elif channel == CommunicationChannel.WHATSAPP:
            return """
DIRETRIZES PARA WHATSAPP:
- Sem assunto
- Estrutura: Apresentação → Conexão → Valor → CTA
- Tamanho: 2-3 parágrafos curtos
- Formato: Informal mas profissional
- CTA: Conversa ou agendamento simples
"""
        else:
            return """
DIRETRIZES GERAIS:
- Mantenha profissional mas acessível
- Foque no valor para o destinatário
- CTA claro e de baixo compromisso
"""
    
    def _parse_message_response(self, response: str, channel: CommunicationChannel) -> PersonalizedMessage:
        """Parse LLM response into PersonalizedMessage"""
        
        try:
            # Clean response and extract JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            
            # Extract subject line (only for email)
            subject_line = None
            if channel == CommunicationChannel.EMAIL:
                subject_line = data.get('subject_line', 'Oportunidade para [Nome da Empresa]')
            
            return PersonalizedMessage(
                channel=channel,
                subject_line=subject_line,
                message_body=data.get('message_body', 'Mensagem não disponível'),
                call_to_action=data.get('call_to_action', 'Gostaria de agendar uma conversa?'),
                personalization_elements=data.get('personalization_elements', ['Nome da empresa', 'Setor', 'Desafios']),
                estimated_read_time=data.get('estimated_read_time', 60),
                ab_variant=None  # Can be set later for A/B testing
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse message JSON response: {e}")
            # Return fallback message
            return self._create_fallback_message(channel)
        
        except Exception as e:
            logger.error(f"Error parsing message response: {e}")
            raise
    
    def _create_fallback_message(self, channel: CommunicationChannel) -> PersonalizedMessage:
        """Create a fallback message when parsing fails"""
        
        if channel == CommunicationChannel.EMAIL:
            return PersonalizedMessage(
                channel=channel,
                subject_line="Oportunidade de otimização para sua empresa",
                message_body="""Olá,

Espero que esteja bem. Tenho acompanhado o trabalho da sua empresa e acredito que posso agregar valor com nossa solução.

Baseado no que vi sobre seus desafios atuais, nossa plataforma pode ajudar a otimizar processos e reduzir custos operacionais.

Gostaria de agendar 15 minutos para uma conversa rápida sobre como isso pode se aplicar ao seu contexto específico?

Atenciosamente""",
                call_to_action="Agendar conversa de 15 minutos",
                personalization_elements=["Nome da empresa", "Setor"],
                estimated_read_time=45
            )
        else:
            return PersonalizedMessage(
                channel=channel,
                subject_line=None,
                message_body="""Olá! Tenho acompanhado o trabalho da sua empresa e acredito que nossa solução pode agregar valor aos seus processos atuais.

Gostaria de trocar uma ideia rápida sobre como isso pode se aplicar ao seu contexto?""",
                call_to_action="Conversar sobre oportunidades",
                personalization_elements=["Nome da empresa"],
                estimated_read_time=30
            )
    
    def _extract_company_name(self, lead_with_strategy: LeadWithStrategy) -> str:
        """Extract company name from Google search data or URL"""
        
        # Try to get from Google search title
        google_data = lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.site_data.google_search_data
        if google_data and google_data.title:
            # Clean up Google title to extract company name
            title = google_data.title
            # Remove common suffixes and patterns
            company_name = title.split(" - ")[0].split(" | ")[0].split(": ")[0]
            company_name = re.sub(r'\s*\([^)]*\)', '', company_name)  # Remove parentheses
            if len(company_name) > 5 and not any(char in company_name.lower() for char in ['http', 'www', '.com']):
                return company_name.strip()
        
        # Fallback to domain name
        url = str(lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.site_data.url)
        domain = url.replace('https://', '').replace('http://', '').split('/')[0]
        domain = domain.replace('www.', '')
        return domain.split('.')[0].title()
    
    def _generate_lead_id(self, url: str) -> str:
        """Generate a unique lead ID"""
        import hashlib
        return hashlib.md5(f"{url}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
    
    def _calculate_confidence_score(self, lead_with_strategy: LeadWithStrategy) -> float:
        """Calculate confidence score based on data quality"""
        
        score = 0.0
        
        # Base score from relevance
        relevance = lead_with_strategy.lead_with_persona.analyzed_lead.analysis.relevance_score
        score += relevance * 0.4
        
        # Extraction success bonus
        if lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.extraction_successful:
            score += 0.2
        
        # Company data quality
        analysis = lead_with_strategy.lead_with_persona.analyzed_lead.analysis
        if analysis.main_services and len(analysis.main_services) > 0:
            score += 0.1
        if analysis.potential_challenges and len(analysis.potential_challenges) > 0:
            score += 0.1
        if analysis.company_sector and analysis.company_sector != "Não determinado":
            score += 0.1
        
        # Persona completeness
        persona = lead_with_strategy.lead_with_persona.persona
        if persona.key_responsibilities and len(persona.key_responsibilities) > 1:
            score += 0.05
        if persona.professional_goals and len(persona.professional_goals) > 1:
            score += 0.05
        
        return min(score, 1.0)  # Cap at 1.0
