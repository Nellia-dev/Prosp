"""
Approach Strategy Agent for Nellia Prospector
Develops strategic approach plans for leads with personas.
"""

from typing import Optional
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
from core_logic.llm_client import LLMClientBase

class ApproachStrategyAgent(BaseAgent[LeadWithPersona, LeadWithStrategy]):
    """Agent responsible for creating strategic approach plans for leads"""
    
    def __init__(self, llm_client: Optional[LLMClientBase] = None, product_service_context: str = ""):
        super().__init__(
            name="ApproachStrategyAgent",
            description="Develops strategic approach plans for leads with personas",
            llm_client=llm_client,
            config={"product_service_context": product_service_context}
        )
        self.product_service_context = product_service_context
    
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
        prompt = self._build_strategy_prompt(lead_with_persona)
        
        # Generate LLM response
        response = self.generate_llm_response(prompt)
        
        # Parse the response
        strategy_data = self.parse_llm_json_response(response, None)
        
        # Create ApproachStrategy from parsed data
        strategy = self._create_approach_strategy(strategy_data)
        
        # Build and return result
        result = LeadWithStrategy(
            lead_with_persona=lead_with_persona,
            strategy=strategy,
            strategy_timestamp=datetime.now()
        )
        
        logger.info(f"Strategy created: {strategy.primary_channel.value} approach for {strategy.first_interaction_goal}")
        return result
    
    def _build_strategy_prompt(self, lead_with_persona: LeadWithPersona) -> str:
        """Build the prompt for strategy creation"""
        
        analyzed_lead = lead_with_persona.analyzed_lead
        persona = lead_with_persona.persona
        
        # Extract Brazilian business culture context
        brazilian_context = self._get_brazilian_business_context(analyzed_lead.analysis.company_sector)
        
        return f"""Você é um Estrategista de Vendas B2B Sênior especializado no mercado brasileiro.
Sua tarefa é desenvolver um plano de abordagem personalizado e eficaz para conquistar o tomador de decisão identificado.

OBJETIVO: Criar uma estratégia que resulte em 527% ROI através de abordagem altamente personalizada.

CONTEXTO DA EMPRESA:
- URL: {analyzed_lead.validated_lead.site_data.url}
- Setor: {analyzed_lead.analysis.company_sector}
- Tamanho: {analyzed_lead.analysis.company_size_estimate or 'Não determinado'}
- Principais serviços: {', '.join(analyzed_lead.analysis.main_services)}
- Desafios identificados: {', '.join(analyzed_lead.analysis.potential_challenges)}
- Cultura: {analyzed_lead.analysis.company_culture_values or 'Não determinada'}
- Diagnóstico: {analyzed_lead.analysis.general_diagnosis}

CONTEXTO DA PERSONA ({persona.likely_role}):
- Nome fictício: {persona.fictional_name}
- Responsabilidades: {', '.join(persona.key_responsibilities)}
- Objetivos profissionais: {', '.join(persona.professional_goals)}
- Principais desafios: {', '.join(persona.main_challenges)}
- Motivações: {', '.join(persona.motivations)}
- Estilo de comunicação: {persona.communication_style}
- Processo de decisão: {persona.decision_making_process or 'Não especificado'}

PRODUTO/SERVIÇO NELLIA:
{self.product_service_context or "Soluções de IA para otimização de processos de vendas e geração de leads B2B"}

{brazilian_context}

INSTRUÇÕES:
Desenvolva um plano de abordagem estratégico que conecte as necessidades específicas desta persona 
com os benefícios do nosso produto/serviço. Foque na criação de valor e relacionamento.

Responda APENAS com JSON válido no seguinte formato:
{{
    "primary_channel": "email|linkedin|whatsapp|phone",
    "secondary_channel": "email|linkedin|whatsapp|phone|null",
    "tone_of_voice": "Tom e estilo de comunicação recomendado",
    "key_value_propositions": ["proposta1", "proposta2", "proposta3"],
    "talking_points": ["ponto1", "ponto2", "ponto3"],
    "potential_objections": {{
        "objecao1": "resposta consultiva 1",
        "objecao2": "resposta consultiva 2",
        "objecao3": "resposta consultiva 3"
    }},
    "opening_questions": ["pergunta1", "pergunta2"],
    "first_interaction_goal": "Objetivo específico e mensurável do primeiro contato",
    "follow_up_strategy": "Estratégia detalhada de follow-up"
}}

DIRETRIZES CRÍTICAS:
- Escolha o canal baseado no perfil da persona e cultura da empresa
- Conecte DIRETAMENTE nossos benefícios aos desafios identificados
- Antecipe objeções e prepare respostas consultivas (não defensivas)
- Sugira perguntas que despertem curiosidade genuína
- Seja específico e acionável - evite generalidades
- Considere o contexto brasileiro de relacionamento antes do negócio"""
    
    def _get_brazilian_business_context(self, sector: str) -> str:
        """Get Brazilian business context based on sector"""
        
        context_map = {
            "tecnologia": """
CONTEXTO BRASILEIRO - SETOR TECNOLOGIA:
- Decisores são técnicos e valorizam dados concretos
- Comunicação pode ser mais direta e técnica
- LinkedIn é muito utilizado para networking
- Preferem casos de uso e ROI comprovados""",
            
            "serviços": """
CONTEXTO BRASILEIRO - SETOR SERVIÇOS:
- Relacionamento é fundamental - invista tempo nisso
- Comunicação mais consultiva e menos técnica
- Referências e networking são muito valorizados
- Processo de decisão pode ser mais longo""",
            
            "indústria": """
CONTEXTO BRASILEIRO - SETOR INDUSTRIAL:
- Conservadores e focados em ROI tangível
- Preferem reuniões presenciais ou por telefone
- Hierarquia bem definida - respeite a cadeia
- Casos de sucesso no setor são essenciais"""
        }
        
        # Find matching context or use default
        for key, context in context_map.items():
            if key.lower() in sector.lower():
                return context
                
        return """
CONTEXTO BRASILEIRO GERAL:
- Relacionamento precede negócio - invista na conexão pessoal
- Respeite hierarquia e formalidade apropriada
- Seja direto mas cordial
- Demonstre conhecimento do mercado brasileiro"""
    
    def _create_approach_strategy(self, strategy_data: dict) -> ApproachStrategy:
        """Create ApproachStrategy from parsed JSON data"""
        
        try:
            # Map channel strings to enum values
            primary_channel = self._map_channel(strategy_data.get('primary_channel', 'email'))
            secondary_channel = None
            
            secondary_str = strategy_data.get('secondary_channel')
            if secondary_str and secondary_str != 'null':
                secondary_channel = self._map_channel(secondary_str)
            
            return ApproachStrategy(
                primary_channel=primary_channel,
                secondary_channel=secondary_channel,
                tone_of_voice=strategy_data.get('tone_of_voice', 'Profissional e consultivo'),
                key_value_propositions=strategy_data.get('key_value_propositions', ['Otimização de processos', 'Aumento de eficiência']),
                talking_points=strategy_data.get('talking_points', ['Benefícios específicos para o setor']),
                potential_objections=strategy_data.get('potential_objections', {
                    'já temos uma solução': 'Entendo. Que resultados vocês têm obtido?',
                    'não temos orçamento': 'Compreendo. Vamos explorar o ROI potencial?'
                }),
                opening_questions=strategy_data.get('opening_questions', ['Como vocês lidam atualmente com esse desafio?']),
                first_interaction_goal=strategy_data.get('first_interaction_goal', 'Despertar interesse e compreender necessidades'),
                follow_up_strategy=strategy_data.get('follow_up_strategy', 'Follow-up educacional em 3-5 dias úteis')
            )
            
        except Exception as e:
            logger.warning(f"Failed to create strategy from data: {e}")
            # Return fallback strategy
            return ApproachStrategy(
                primary_channel=CommunicationChannel.EMAIL,
                secondary_channel=CommunicationChannel.LINKEDIN,
                tone_of_voice="Profissional e consultivo",
                key_value_propositions=[
                    "Otimização de processos de vendas",
                    "Aumento de 527% no ROI",
                    "Personalização de abordagem em escala"
                ],
                talking_points=[
                    "Cases de sucesso no mercado brasileiro",
                    "Integração com processos existentes",
                    "Suporte especializado em português"
                ],
                potential_objections={
                    "já temos uma solução": "Entendo. Como está funcionando? Vamos comparar resultados?",
                    "não temos orçamento": "Faz sentido. Vamos calcular o ROI potencial primeiro?",
                    "não é prioridade": "Compreendo. Quando seria um bom momento para reavaliarmos?"
                },
                opening_questions=[
                    "Como vocês lidam atualmente com a geração de leads qualificados?",
                    "Qual o maior desafio no processo comercial atual?"
                ],
                first_interaction_goal="Despertar interesse e compreender necessidades específicas",
                follow_up_strategy="Follow-up com conteúdo educacional personalizado"
            )
    
    def _map_channel(self, channel_str: str) -> CommunicationChannel:
        """Map string to CommunicationChannel enum"""
        channel_mapping = {
            'email': CommunicationChannel.EMAIL,
            'linkedin': CommunicationChannel.LINKEDIN,
            'whatsapp': CommunicationChannel.WHATSAPP,
            'phone': CommunicationChannel.PHONE
        }
        return channel_mapping.get(channel_str.lower(), CommunicationChannel.EMAIL)
