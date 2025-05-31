"""
Approach Strategy Agent for Nellia Prospector
Develops strategic approach plans for leads with personas.
"""

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
import json

from data_models.lead_structures import (
    LeadWithPersona, 
    LeadWithStrategy, 
    ApproachStrategy,
    CommunicationChannel
)
from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClient


class ApproachStrategyAgent(BaseAgent):
    """Agent responsible for creating strategic approach plans for leads"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, product_service_context: str = ""):
        super().__init__(agent_name="ApproachStrategyAgent")
        self.llm_client = llm_client or LLMClient()
        self.product_service_context = product_service_context
    
    def execute(self, lead_with_persona: LeadWithPersona) -> LeadWithStrategy:
        """
        Create a strategic approach plan for the lead with persona
        
        Args:
            lead_with_persona: LeadWithPersona with company analysis and persona
            
        Returns:
            LeadWithStrategy with complete approach strategy
        """
        self.start_execution()
        
        try:
            logger.info(f"Creating strategy for lead: {lead_with_persona.analyzed_lead.validated_lead.site_data.url}")
            
            # Create strategy using LLM
            strategy = self._create_strategy(lead_with_persona)
            
            # Build result
            result = LeadWithStrategy(
                lead_with_persona=lead_with_persona,
                strategy=strategy,
                strategy_timestamp=datetime.now()
            )
            
            self.end_execution(success=True)
            logger.info(f"Strategy created: {strategy.primary_channel.value} approach for {strategy.first_interaction_goal}")
            
            return result
            
        except Exception as e:
            self.end_execution(success=False, error=str(e))
            logger.error(f"Error creating strategy: {e}")
            raise
    
    def _create_strategy(self, lead_with_persona: LeadWithPersona) -> ApproachStrategy:
        """Create strategy using LLM analysis"""
        
        # Prepare context for LLM
        strategy_context = {
            "url": str(lead_with_persona.analyzed_lead.validated_lead.site_data.url),
            "company_sector": lead_with_persona.analyzed_lead.analysis.company_sector,
            "company_size": lead_with_persona.analyzed_lead.analysis.company_size_estimate,
            "main_services": lead_with_persona.analyzed_lead.analysis.main_services,
            "challenges": lead_with_persona.analyzed_lead.analysis.potential_challenges,
            "culture": lead_with_persona.analyzed_lead.analysis.company_culture_values,
            "persona_role": lead_with_persona.persona.likely_role,
            "persona_name": lead_with_persona.persona.fictional_name,
            "persona_responsibilities": lead_with_persona.persona.key_responsibilities,
            "persona_goals": lead_with_persona.persona.professional_goals,
            "persona_challenges": lead_with_persona.persona.main_challenges,
            "persona_motivations": lead_with_persona.persona.motivations,
            "communication_style": lead_with_persona.persona.communication_style,
            "decision_making": lead_with_persona.persona.decision_making_process,
            "product_service": self.product_service_context
        }
        
        prompt = self._build_strategy_prompt(strategy_context)
        
        # Get LLM response
        response = self.llm_client.generate_text(prompt)
        
        # Parse response into ApproachStrategy
        return self._parse_strategy_response(response)
    
    def _build_strategy_prompt(self, context: dict) -> str:
        """Build the prompt for strategy creation"""
        
        return f"""
Você é um Estrategista de Vendas e Abordagem Consultiva Sênior.
Sua tarefa é desenvolver um plano de abordagem personalizado e eficaz para a persona identificada na empresa analisada.

CONTEXTO DA EMPRESA:
- URL: {context['url']}
- Setor: {context['company_sector']}
- Tamanho: {context['company_size']}
- Principais serviços: {', '.join(context['main_services'])}
- Desafios identificados: {', '.join(context['challenges'])}
- Cultura: {context['culture']}

CONTEXTO DA PERSONA ({context['persona_role']}):
- Nome fictício: {context['persona_name']}
- Responsabilidades: {', '.join(context['persona_responsibilities'])}
- Objetivos profissionais: {', '.join(context['persona_goals'])}
- Principais desafios: {', '.join(context['persona_challenges'])}
- Motivações: {', '.join(context['persona_motivations'])}
- Estilo de comunicação: {context['communication_style']}
- Processo de decisão: {context['decision_making']}

PRODUTO/SERVIÇO A SER OFERECIDO:
{context['product_service']}

INSTRUÇÕES:
Desenvolva um plano de abordagem estratégico específico para esta persona e empresa. Responda no formato JSON com as seguintes chaves:

{{
    "primary_channel": "email|linkedin|whatsapp|phone",
    "secondary_channel": "email|linkedin|whatsapp|phone|null",
    "tone_of_voice": "Tom e estilo de comunicação recomendado",
    "key_value_propositions": ["valor1", "valor2", "valor3"],
    "talking_points": ["ponto1", "ponto2", "ponto3"],
    "potential_objections": {{
        "objecao1": "resposta1",
        "objecao2": "resposta2",
        "objecao3": "resposta3"
    }},
    "opening_questions": ["pergunta1", "pergunta2"],
    "first_interaction_goal": "Objetivo específico do primeiro contato",
    "follow_up_strategy": "Estratégia de follow-up se necessário"
}}

DIRETRIZES:
- Base a estratégia no setor, persona e características da empresa
- Escolha o canal mais apropriado considerando o perfil da persona
- Foque nos benefícios mais relevantes do produto/serviço para ESTA persona
- Antecipe objeções comuns e prepare respostas consultivas
- Sugira perguntas abertas que despertem interesse genuíno
- Seja específico e acionável

Responda APENAS com o JSON válido, sem explicações adicionais.
"""
    
    def _parse_strategy_response(self, response: str) -> ApproachStrategy:
        """Parse LLM response into ApproachStrategy"""
        
        try:
            # Clean response and extract JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            
            # Map channel strings to enum values
            primary_channel = self._map_channel(data.get('primary_channel', 'email'))
            secondary_channel = None
            if data.get('secondary_channel') and data.get('secondary_channel') != 'null':
                secondary_channel = self._map_channel(data.get('secondary_channel'))
            
            return ApproachStrategy(
                primary_channel=primary_channel,
                secondary_channel=secondary_channel,
                tone_of_voice=data.get('tone_of_voice', 'Profissional e direto'),
                key_value_propositions=data.get('key_value_propositions', ['Benefícios não especificados']),
                talking_points=data.get('talking_points', ['Pontos não especificados']),
                potential_objections=data.get('potential_objections', {'objeção': 'resposta'}),
                opening_questions=data.get('opening_questions', ['Como está lidando com...?']),
                first_interaction_goal=data.get('first_interaction_goal', 'Despertar interesse e agendar conversa'),
                follow_up_strategy=data.get('follow_up_strategy', 'Follow-up em 3-5 dias úteis')
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse strategy JSON response: {e}")
            # Return fallback strategy
            return ApproachStrategy(
                primary_channel=CommunicationChannel.EMAIL,
                secondary_channel=CommunicationChannel.LINKEDIN,
                tone_of_voice="Profissional e consultivo",
                key_value_propositions=["Otimização de processos", "Redução de custos", "Aumento de eficiência"],
                talking_points=["Benefícios específicos para o setor", "Cases de sucesso similares"],
                potential_objections={
                    "já temos uma solução": "Entendo. Que resultados vocês têm obtido com a solução atual?",
                    "não temos orçamento": "Compreendo a preocupação. Vamos explorar o ROI potencial primeiro?",
                    "não é prioridade": "Faz sentido. Quando seria um bom momento para reavaliarmos?"
                },
                opening_questions=[
                    "Como vocês lidam atualmente com [desafio identificado]?",
                    "Qual o maior desafio que vocês enfrentam em [área relevante]?"
                ],
                first_interaction_goal="Despertar interesse e compreender necessidades específicas",
                follow_up_strategy="Follow-up educacional com conteúdo relevante"
            )
        
        except Exception as e:
            logger.error(f"Error parsing strategy response: {e}")
            raise
    
    def _map_channel(self, channel_str: str) -> CommunicationChannel:
        """Map string to CommunicationChannel enum"""
        channel_mapping = {
            'email': CommunicationChannel.EMAIL,
            'linkedin': CommunicationChannel.LINKEDIN,
            'whatsapp': CommunicationChannel.WHATSAPP,
            'phone': CommunicationChannel.PHONE
        }
        return channel_mapping.get(channel_str.lower(), CommunicationChannel.EMAIL)
