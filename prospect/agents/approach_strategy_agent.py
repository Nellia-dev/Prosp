"""
Approach Strategy Agent for Nellia Prospector
Develops strategic approach plans for leads with personas.
"""

from typing import Optional, Dict, List # Added Dict, List
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
        response_text = self.generate_llm_response(prompt)
        
        # Parse the response
        strategy_data = self.parse_llm_json_response(response_text, None) # Changed variable name for clarity
        
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
    
    def _build_strategy_prompt(self, lead_with_persona: LeadWithPersona) -> str:
        """Build the prompt for strategy creation - REFINED"""
        
        analyzed_lead = lead_with_persona.analyzed_lead
        persona = lead_with_persona.persona
        
        # Extract Brazilian business culture context
        brazilian_context_str = self._get_brazilian_business_context(analyzed_lead.analysis.company_sector or "Geral")
        
        # Ensure product_service_context has a default if empty for the prompt
        product_context_for_prompt = self.product_service_context or "nossas soluções de IA para otimização de processos de vendas e geração de leads B2B"

        # Constructing context strings carefully to avoid issues with None or empty lists
        company_services_str = ', '.join(analyzed_lead.analysis.main_services) if analyzed_lead.analysis.main_services else "Não detalhado na análise inicial."
        company_challenges_str = ', '.join(analyzed_lead.analysis.potential_challenges) if analyzed_lead.analysis.potential_challenges else "Não detalhado na análise inicial."

        persona_responsibilities_str = ', '.join(persona.key_responsibilities) if persona.key_responsibilities else "Não detalhado."
        persona_goals_str = ', '.join(persona.professional_goals) if persona.professional_goals else "Não detalhado."
        persona_challenges_str = ', '.join(persona.main_challenges) if persona.main_challenges else "Não detalhado."
        persona_motivations_str = ', '.join(persona.motivations) if persona.motivations else "Não detalhado."

        return f"""Você é um Estrategista de Vendas B2B Sênior, altamente experiente e especializado no mercado brasileiro.
Sua missão é desenvolver um plano de abordagem personalizado e eficaz para o tomador de decisão descrito abaixo, visando maximizar o potencial de conversão e alcançar resultados de alto impacto (ex: um ROI significativo).

INFORMAÇÕES DISPONÍVEIS:

1. CONTEXTO DA EMPRESA ALVO:
   - URL: {analyzed_lead.validated_lead.site_data.url}
   - Setor de Atuação: {analyzed_lead.analysis.company_sector or 'Não Especificado'}
   - Porte Estimado: {analyzed_lead.analysis.company_size_estimate or 'Não Determinado'}
   - Principais Serviços/Produtos: {company_services_str}
   - Desafios Potenciais Identificados: {company_challenges_str}
   - Cultura e Valores (inferidos): {analyzed_lead.analysis.company_culture_values or 'Não foi possível determinar'}
   - Diagnóstico Geral da Empresa: {analyzed_lead.analysis.general_diagnosis or 'Não disponível'}

2. CONTEXTO DA PERSONA (Tomador de Decisão):
   - Nome Fictício (para referência): {persona.fictional_name or 'N/A'}
   - Cargo Provável: {persona.likely_role or 'Não Especificado'}
   - Principais Responsabilidades: {persona_responsibilities_str}
   - Objetivos Profissionais: {persona_goals_str}
   - Seus Maiores Desafios Profissionais: {persona_challenges_str}
   - Fatores de Motivação: {persona_motivations_str}
   - Estilo de Comunicação Preferido: {persona.communication_style or 'Não Especificado'}
   - Processo de Tomada de Decisão (inferido): {persona.decision_making_process or 'Não Especificado'}

3. NOSSO PRODUTO/SERVIÇO:
   "{product_context_for_prompt}"

4. CONTEXTO DO MERCADO BRASILEIRO (para o setor da empresa alvo):
{brazilian_context_str}

INSTRUÇÕES PARA A ESTRATÉGIA DE ABORDAGEM:
Com base em TODAS as informações fornecidas, desenvolva um plano de abordagem estratégico e detalhado.
O plano deve ser prático, acionável e culturalmente adaptado ao Brasil.
Conecte as necessidades específicas da persona e os desafios da empresa diretamente aos benefícios do nosso produto/serviço.
O foco é em criar valor, construir relacionamento e facilitar uma decisão de compra favorável.

FORMATO DA RESPOSTA:
Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo.
NÃO inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

SCHEMA JSON ESPERADO:
{{
    "primary_channel": "string - O canal de comunicação MAIS recomendado para o primeiro contato. Escolha entre: 'email', 'linkedin', 'whatsapp', 'phone'.",
    "secondary_channel": "string | null - Um canal alternativo ou de follow-up, se apropriado. Escolha entre: 'email', 'linkedin', 'whatsapp', 'phone', ou use null se não houver um secundário claro.",
    "tone_of_voice": "string - Descreva o tom de voz recomendado (ex: 'Consultivo e educacional, focado em parceria', 'Formal, direto e respeitoso à hierarquia', 'Amigável, colaborativo e inovador'). Considere a persona e o contexto brasileiro.",
    "key_value_propositions": ["string", ...] - Lista de 2-3 propostas de valor CHAVE e concisas, destacando como nosso produto/serviço resolve os desafios da persona/empresa ou ajuda a atingir seus objetivos. Ex: 'Redução de custos operacionais em X% através de Y', 'Aumento da eficiência da equipe de vendas com Z'.",
    "talking_points": ["string", ...] - Lista de 2-3 pontos de conversa principais para usar na interação inicial, derivados das propostas de valor, mas formulados de forma mais conversacional.",
    "potential_objections": {{ "string": "string", ... }} - Dicionário onde as chaves são objeções comuns previstas (ex: 'Já temos uma solução', 'Não temos orçamento agora', 'Isso não é prioridade') e os valores são respostas consultivas e eficazes, focadas em entender melhor e agregar valor, em vez de serem defensivas.",
    "opening_questions": ["string", ...] - Lista de 1-2 perguntas abertas, instigantes e específicas para o contexto do lead, para iniciar a conversa, demonstrar pesquisa e descobrir mais sobre suas necessidades atuais.",
    "first_interaction_goal": "string - O objetivo principal, específico e mensurável do primeiro contato (ex: 'Agendar uma conversa de diagnóstico de 15 minutos para explorar [desafio específico]', 'Obter confirmação de que [desafio X] é relevante e entender o impacto atual', 'Apresentar um case de sucesso similar e colher feedback inicial').",
    "follow_up_strategy": "string - Descreva uma estratégia de follow-up concisa e lógica, com 2-3 passos, caso o primeiro contato não gere o resultado esperado (ex: '1. Enviar um artigo/case de estudo relevante via LinkedIn após 3 dias, mencionando um ponto da conversa inicial. 2. Se não houver resposta, tentar um contato telefônico breve após 1 semana para oferecer ajuda em um desafio específico. 3. Convidar para um webinar relevante se os passos anteriores não avançarem.')."
}}

LEMBRETES FINAIS:
- Preencha TODOS os campos do JSON conforme o schema.
- Para campos de lista (arrays), se nenhuma informação específica for gerada, retorne uma lista vazia `[]`.
- Para `secondary_channel`, se não aplicável, use `null`.
- Baseie TODA a estratégia estritamente nas informações fornecidas. Não invente detalhes não presentes no contexto.
- A qualidade e personalização da estratégia são cruciais.
"""
    
    def _get_brazilian_business_context(self, sector: Optional[str]) -> str: # sector can be None
        """Get Brazilian business context based on sector"""
        sector_lower = (sector or "").lower() # Handle None case for sector
        
        context_map = {
            "tecnologia": """- Setor de Tecnologia: Decisores podem ser técnicos e valorizam dados concretos, ROI claro e inovação. Comunicação pode ser mais direta. LinkedIn é muito utilizado. Cases de sucesso e demonstrações são eficazes.""",
            "serviços": """- Setor de Serviços: Relacionamento pessoal e confiança são fundamentais. Comunicação consultiva e menos agressiva. Networking e referências são muito valorizados. Processo de decisão pode ser colaborativo e mais longo.""",
            "indústria": """- Setor Industrial: Tendência a ser mais conservador, focado em ROI tangível, eficiência e confiabilidade. Hierarquia pode ser importante. Casos de sucesso e conhecimento técnico do setor são diferenciais."""
        }
        
        specific_context = ""
        for key, context_text in context_map.items():
            if key in sector_lower:
                specific_context = context_text
                break

        general_context = """- Contexto Geral Brasileiro: Relacionamento muitas vezes precede o negócio; invista na conexão pessoal (mesmo virtualmente). A comunicação tende a ser mais indireta e cordial do que em algumas outras culturas; evite ser excessivamente direto ou transacional no primeiro contato. Demonstre conhecimento e interesse genuíno pelo mercado e pela empresa do lead. Flexibilidade e paciência podem ser necessárias."""

        return f"{specific_context}\n{general_context}".strip()
    
    def _create_approach_strategy(self, strategy_data: Optional[Dict[str, Any]]) -> ApproachStrategy: # strategy_data can be None
        """Create ApproachStrategy from parsed JSON data"""
        
        if not strategy_data: # Handle cases where JSON parsing failed and returned None
            logger.warning("Strategy data is None, returning fallback strategy.")
            strategy_data = {} # Initialize to empty dict to allow .get() to work

        try:
            primary_channel_str = strategy_data.get('primary_channel', 'email')
            primary_channel = self._map_channel(primary_channel_str)
            
            secondary_channel_str = strategy_data.get('secondary_channel')
            secondary_channel = None
            if secondary_channel_str and secondary_channel_str.lower() != 'null':
                secondary_channel = self._map_channel(secondary_channel_str)
            
            # Ensure lists and dicts are correctly defaulted if missing or not of expected type
            key_value_propositions = strategy_data.get('key_value_propositions', [])
            if not isinstance(key_value_propositions, list): key_value_propositions = ['Proposta de valor padrão devido a erro de parsing']

            talking_points = strategy_data.get('talking_points', [])
            if not isinstance(talking_points, list): talking_points = ['Ponto de conversa padrão devido a erro de parsing']

            potential_objections = strategy_data.get('potential_objections', {})
            if not isinstance(potential_objections, dict): potential_objections = {'objeção_padrão': 'resposta padrão devido a erro de parsing'}

            opening_questions = strategy_data.get('opening_questions', [])
            if not isinstance(opening_questions, list): opening_questions = ['Pergunta padrão devido a erro de parsing']


            return ApproachStrategy(
                primary_channel=primary_channel,
                secondary_channel=secondary_channel,
                tone_of_voice=strategy_data.get('tone_of_voice', 'Profissional e consultivo'),
                key_value_propositions=key_value_propositions,
                talking_points=talking_points,
                potential_objections=potential_objections,
                opening_questions=opening_questions,
                first_interaction_goal=strategy_data.get('first_interaction_goal', 'Despertar interesse e compreender necessidades'),
                follow_up_strategy=strategy_data.get('follow_up_strategy', 'Follow-up educacional em 3-5 dias úteis')
            )
            
        except Exception as e:
            logger.warning(f"Failed to create strategy from data due to: {e}. Data: {strategy_data}")
            # Return fallback strategy
            return ApproachStrategy(
                primary_channel=CommunicationChannel.EMAIL,
                secondary_channel=CommunicationChannel.LINKEDIN,
                tone_of_voice="Profissional e consultivo (fallback)",
                key_value_propositions=[
                    "Otimização de processos de vendas (fallback)",
                    "Aumento de ROI (fallback)",
                    "Personalização de abordagem (fallback)"
                ],
                talking_points=[
                    "Cases de sucesso no mercado brasileiro (fallback)",
                    "Integração com processos existentes (fallback)",
                    "Suporte especializado (fallback)"
                ],
                potential_objections={
                    "custo": "Entendo a preocupação com o orçamento. Podemos explorar opções que se encaixem ou demonstrar o ROI que justifica o investimento? (fallback)",
                    "satisfeito_com_solucao_atual": "Que ótimo que já possuem uma solução! Quais aspectos vocês mais valorizam nela e há algo que poderia ser ainda melhor? (fallback)"
                },
                opening_questions=[
                    "Quais são seus maiores desafios atualmente na área de [relacionada ao produto/serviço]? (fallback)",
                    "Como sua equipe mede o sucesso em relação a [objetivo que o produto/serviço atende]? (fallback)"
                ],
                first_interaction_goal="Estabelecer um primeiro contato e avaliar o interesse inicial (fallback)",
                follow_up_strategy="Enviar material de apoio e agendar conversa se houver interesse (fallback)"
            )
    
    def _map_channel(self, channel_str: Optional[str]) -> CommunicationChannel: # channel_str can be None
        """Map string to CommunicationChannel enum"""
        channel_mapping = {
            'email': CommunicationChannel.EMAIL,
            'linkedin': CommunicationChannel.LINKEDIN,
            'whatsapp': CommunicationChannel.WHATSAPP,
            'phone': CommunicationChannel.PHONE
        }
        return channel_mapping.get((channel_str or "").lower(), CommunicationChannel.EMAIL) # Default to EMAIL if None or invalid
