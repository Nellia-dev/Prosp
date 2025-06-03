"""
Message Crafting Agent for Nellia Prospector
Creates personalized outreach messages based on strategy and persona.
"""

from typing import Optional
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
from core_logic.llm_client import LLMClientBase

class MessageCraftingAgent(BaseAgent[LeadWithStrategy, FinalProspectPackage]):
    """Agent responsible for creating personalized outreach messages"""
    
    def __init__(self, llm_client: Optional[LLMClientBase] = None):
        super().__init__(
            name="MessageCraftingAgent",
            description="Creates personalized outreach messages for B2B leads",
            llm_client=llm_client
        )
    
    def process(self, lead_with_strategy: LeadWithStrategy) -> FinalProspectPackage:
        """
        Create personalized outreach message for the lead with strategy
        
        Args:
            lead_with_strategy: LeadWithStrategy with complete approach plan
            
        Returns:
            FinalProspectPackage with ready-to-send message
        """
        lead_url = str(lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.site_data.url)
        logger.info(f"Creating message for: {lead_url}")
        
        # Build the prompt for message creation
        prompt = self._build_message_prompt(lead_with_strategy)
        
        # Generate LLM response
        response = self.generate_llm_response(prompt)
        
        # Parse the response
        message_data = self.parse_llm_json_response(response, None)
        
        # Create PersonalizedMessage from parsed data
        message = self._create_personalized_message(message_data, lead_with_strategy.strategy.primary_channel)
        
        # Build final result
        result = FinalProspectPackage(
            lead_with_strategy=lead_with_strategy,
            personalized_message=message,
            processing_complete_timestamp=datetime.now(),
            lead_id=self._generate_lead_id(lead_url),
            confidence_score=self._calculate_confidence_score(lead_with_strategy)
        )
        
        logger.info(f"Message created: {message.channel.value} message with CTA: {message.call_to_action[:50]}...")
        return result
    
    def _build_message_prompt(self, lead_with_strategy: LeadWithStrategy) -> str:
        """Build the prompt for message creation"""
        
        analyzed_lead = lead_with_strategy.lead_with_persona.analyzed_lead
        persona = lead_with_strategy.lead_with_persona.persona
        strategy = lead_with_strategy.strategy
        
        # Extract company name for personalization
        company_name = self._extract_company_name(lead_with_strategy)
        
        # Get channel-specific guidance
        channel_guidance = self._get_channel_guidance(strategy.primary_channel)
        
        return f"""Você é um Redator de Copywriting B2B Sênior especializado em mensagens de primeiro contato no mercado brasileiro.
Sua tarefa é criar uma mensagem altamente personalizada que resulte em resposta positiva e avance para conversação.

OBJETIVO: Criar mensagem que contribua para o objetivo de cresimento do ROI através de personalização e relevância máximas.

CONTEXTO DA EMPRESA:
- Nome: {company_name}
- URL: {analyzed_lead.validated_lead.site_data.url}
- Setor: {analyzed_lead.analysis.company_sector}
- Principais serviços: {', '.join(analyzed_lead.analysis.main_services)}
- Desafios identificados: {', '.join(analyzed_lead.analysis.potential_challenges)}
- Oportunidade: {analyzed_lead.analysis.opportunity_fit}

CONTEXTO DA PERSONA:
- Nome fictício: {persona.fictional_name} ({persona.likely_role})
- Objetivos: {', '.join(persona.professional_goals)}
- Desafios: {', '.join(persona.main_challenges)}
- Estilo de comunicação: {persona.communication_style}
- Busca em soluções: {persona.solution_seeking}

ESTRATÉGIA DE ABORDAGEM:
- Canal primário: {strategy.primary_channel.value}
- Tom de voz: {strategy.tone_of_voice}
- Propostas de valor: {', '.join(strategy.key_value_propositions)}
- Pontos principais: {', '.join(strategy.talking_points)}
- Perguntas de abertura: {', '.join(strategy.opening_questions)}
- Objetivo do contato: {strategy.first_interaction_goal}

PRODUTO/SERVIÇO NELLIA:
{analyzed_lead.product_service_context}

{channel_guidance}

INSTRUÇÕES CRÍTICAS:
Crie uma mensagem que seja:
1. ALTAMENTE PERSONALIZADA para {company_name} e {persona.fictional_name}
2. Demonstre pesquisa genuína sobre a empresa (use informações específicas)
3. Conecte diretamente nossos benefícios aos desafios identificados
4. Use o tom apropriado: {strategy.tone_of_voice}
5. Inclua CTA claro e de baixo atrito
6. Seja concisa mas impactante (respeitando limites do canal)
7. Soe autêntica, não vendedora
8. Considere o contexto brasileiro de relacionamento antes do negócio

Responda APENAS com JSON válido no seguinte formato:
{{
    "subject_line": "Assunto da mensagem (se aplicável para o canal)",
    "message_body": "Corpo completo da mensagem personalizada",
    "call_to_action": "Call-to-action específico e claro",
    "personalization_elements": ["elemento1", "elemento2", "elemento3"],
    "estimated_read_time": 45
}}

DIRETRIZES FINAIS:
- Evite clichês como "espero que esteja bem"
- Use linguagem natural e conversacional
- Demonstre valor antes de pedir algo
- Seja específico sobre o benefício para ESTA empresa
- Mantenha foco na pessoa, não no produto"""
    
    def _get_channel_guidance(self, channel: CommunicationChannel) -> str:
        """Get channel-specific guidance for message creation"""
        
        if channel == CommunicationChannel.EMAIL:
            return """
DIRETRIZES PARA E-MAIL:
- Assunto: Específico, intrigante, sem spam words (máx 50 caracteres)
- Estrutura: Conexão pessoal → Pesquisa demonstrada → Valor → Pergunta/CTA → Assinatura
- Tamanho: 80-120 palavras idealmente
- Formato: Profissional mas não engessado
- CTA: Específico e de baixo compromisso (ex: "conversa de 10 minutos")
- Use quebras de linha para facilitar leitura"""
            
        elif channel == CommunicationChannel.LINKEDIN:
            return """
DIRETRIZES PARA LINKEDIN:
- Sem assunto (mensagem direta ou nota de conexão)
- Estrutura: Conexão/referência → Valor rápido → Pergunta engajante
- Tamanho: 50-80 palavras máximo (LinkedIn tem limite)
- Formato: Conversacional e profissional
- CTA: Convite para conexão ou conversa breve
- Mencione algo específico do perfil deles"""
            
        elif channel == CommunicationChannel.WHATSAPP:
            return """
DIRETRIZES PARA WHATSAPP:
- Sem assunto
- Estrutura: Apresentação → Conexão → Valor → CTA simples
- Tamanho: 2-3 parágrafos curtos
- Formato: Informal mas profissional
- CTA: Conversa ou pergunta simples
- Use emojis com moderação (1-2 no máximo)"""
            
        else:
            return """
DIRETRIZES GERAIS:
- Mantenha profissional mas acessível
- Foque no valor para o destinatário
- CTA claro e de baixo compromisso
- Demonstre pesquisa e personalização"""
    
    def _create_personalized_message(self, message_data: dict, channel: CommunicationChannel) -> PersonalizedMessage:
        """Create PersonalizedMessage from parsed JSON data"""
        
        try:
            # Extract subject line (only for email)
            subject_line = None
            if channel == CommunicationChannel.EMAIL:
                subject_line = message_data.get('subject_line', 'Oportunidade para otimização')
            
            return PersonalizedMessage(
                channel=channel,
                subject_line=subject_line,
                message_body=message_data.get('message_body', 'Mensagem não disponível'),
                call_to_action=message_data.get('call_to_action', 'Gostaria de trocar uma ideia sobre isso?'),
                personalization_elements=message_data.get('personalization_elements', ['Nome da empresa', 'Setor', 'Desafios']),
                estimated_read_time=message_data.get('estimated_read_time', 60),
                ab_variant=None  # Can be set later for A/B testing
            )
            
        except Exception as e:
            logger.warning(f"Failed to create message from data: {e}")
            # Return fallback message
            return self._create_fallback_message(channel)
    
    def _create_fallback_message(self, channel: CommunicationChannel) -> PersonalizedMessage:
        """Create a fallback message when parsing fails"""
        
        if channel == CommunicationChannel.EMAIL:
            return PersonalizedMessage(
                channel=channel,
                subject_line="Oportunidade de otimização identificada",
                message_body="""Olá,

Vi que vocês trabalham com [serviços identificados] e acredito que nossa solução de IA pode agregar valor significativo aos seus processos.

Baseado no que observei sobre os desafios do setor, nossa plataforma já ajudou empresas similares a aumentar a eficiência em até 527%.

Seria interessante trocarmos uma ideia sobre como isso poderia se aplicar à sua realidade?

Atenciosamente,
Equipe Nellia""",
                call_to_action="Conversa de 15 minutos esta semana",
                personalization_elements=["Serviços da empresa", "Desafios do setor"],
                estimated_read_time=30
            )
        else:
            return PersonalizedMessage(
                channel=channel,
                subject_line=None,
                message_body="""Olá! Vi o trabalho que vocês fazem e acredito que nossa solução de IA pode agregar valor aos seus processos atuais.

Já ajudamos empresas do setor a otimizar significativamente seus resultados.

Faria sentido trocarmos uma ideia rápida sobre isso?""",
                call_to_action="Conversa breve sobre oportunidades",
                personalization_elements=["Trabalho da empresa"],
                estimated_read_time=20
            )
    
    def _extract_company_name(self, lead_with_strategy: LeadWithStrategy) -> str:
        """Extract company name from Google search data or URL"""
        
        # Try to get from Google search title
        site_data = lead_with_strategy.lead_with_persona.analyzed_lead.validated_lead.site_data
        if site_data.google_search_data and site_data.google_search_data.title:
            title = site_data.google_search_data.title
            # Clean up Google title to extract company name
            company_name = title.split(" - ")[0].split(" | ")[0].split(": ")[0]
            company_name = re.sub(r'\s*\([^)]*\)', '', company_name)  # Remove parentheses
            if len(company_name) > 5 and not any(char in company_name.lower() for char in ['http', 'www', '.com']):
                return company_name.strip()
        
        # Fallback to domain name
        url = str(site_data.url)
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
