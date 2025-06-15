"""
Message Crafting Agent for Nellia Prospector
Creates personalized outreach messages based on strategy and persona.
"""

from typing import Optional, List # Added List
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
    
    def __init__(self, llm_client: Optional[LLMClientBase] = None, **kwargs): # Added **kwargs
        super().__init__(
            name="MessageCraftingAgent",
            description="Creates personalized outreach messages for B2B leads",
            llm_client=llm_client,
            **kwargs # Pass **kwargs
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
        logger.info(f"✍️ MESSAGE CRAFTING AGENT STARTING for: {lead_url}")
        
        # Build the prompt for message creation
        prompt = self._build_message_prompt(lead_with_strategy)
        
        # Generate LLM response
        llm_response_str = self.generate_llm_response(prompt) # Renamed for clarity
        
        # Parse the response
        message_data_dict = self.parse_llm_json_response(llm_response_str, None) # Expects dict from JSON
        
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
    
    def _build_message_prompt(self, lead_with_strategy: LeadWithStrategy) -> str:
        """Build the prompt for message creation - REFINED"""
        
        analyzed_lead = lead_with_strategy.lead_with_persona.analyzed_lead
        persona = lead_with_strategy.lead_with_persona.persona
        strategy = lead_with_strategy.strategy
        
        company_name = self._extract_company_name(lead_with_strategy)
        channel_guidance = self._get_channel_guidance(strategy.primary_channel)
        
        # Helper for joining lists or providing 'N/A'
        def join_list_or_na(lst: Optional[List[str]]) -> str:
            return ', '.join(lst) if lst and len(lst) > 0 else 'N/A'

        # Refined prompt template
        return f"""Você é um Redator de Copywriting B2B Estratégico Sênior, especialista em criar mensagens de primeiro contato altamente personalizadas e eficazes, com profundo conhecimento do mercado brasileiro e suas nuances culturais.
Sua tarefa é criar uma mensagem que gere engajamento genuíno, construa rapport e motive uma resposta positiva, avançando a conversa para o próximo estágio definido no objetivo do contato.

OBJETIVO PRINCIPAL DA MENSAGEM: Contribuir para o crescimento do ROI através de uma abordagem de personalização máxima e relevância contextual.

CONTEXTO COMPLETO DO LEAD E ESTRATÉGIA (fornecido pela equipe de estratégia):

1.  EMPRESA ALVO:
    - Nome: {company_name}
    - URL: {analyzed_lead.validated_lead.site_data.url}
    - Setor: {analyzed_lead.analysis.company_sector or 'N/A'}
    - Principais Serviços/Produtos da Empresa Alvo: {join_list_or_na(analyzed_lead.analysis.main_services)}
    - Desafios Identificados da Empresa Alvo: {join_list_or_na(analyzed_lead.analysis.potential_challenges)}
    - Oportunidade Percebida para Nós: {analyzed_lead.analysis.opportunity_fit or 'N/A'}

2.  PERSONA (Tomador de Decisão na Empresa Alvo):
    - Nome Fictício: {persona.fictional_name or 'N/A'} ({persona.likely_role or 'Cargo não especificado'})
    - Objetivos Profissionais Chave: {join_list_or_na(persona.professional_goals)}
    - Seus Principais Desafios: {join_list_or_na(persona.main_challenges)}
    - Estilo de Comunicação Preferido: {persona.communication_style or 'Não especificado'}
    - Como Busca Soluções: {persona.solution_seeking or 'Não especificado'}

3.  ESTRATÉGIA DE ABORDAGEM DEFINIDA:
    - Canal Primário Selecionado: {strategy.primary_channel.value}
    - Tom de Voz Recomendado: {strategy.tone_of_voice}
    - Propostas de Valor Chave para este Lead: {join_list_or_na(strategy.key_value_propositions)}
    - Principais Pontos de Conversa (Talking Points): {join_list_or_na(strategy.talking_points)}
    - Perguntas de Abertura Sugeridas: {join_list_or_na(strategy.opening_questions)}
    - Objetivo Específico deste Primeiro Contato: {strategy.first_interaction_goal}

4.  NOSSO PRODUTO/SERVIÇO (que estamos oferecendo):
    "{analyzed_lead.product_service_context or 'Nossa solução inovadora'}"

5.  DIRETRIZES ESPECÍFICAS PARA O CANAL '{strategy.primary_channel.value}':
{channel_guidance}

INSTRUÇÕES CRÍTICAS PARA A MENSAGEM:
1.  **Ultra-Personalização:** A mensagem DEVE ser percebida como única para {company_name} e {persona.fictional_name}. Referencie informações específicas do contexto fornecido.
2.  **Demonstre Pesquisa:** Mostre que você entende os desafios e objetivos da empresa e da persona.
3.  **Conexão Direta de Valor:** Conecte CLARAMENTE os benefícios do NOSSO PRODUTO/SERVIÇO aos desafios/objetivos identificados. Use as "Propostas de Valor Chave".
4.  **Tom de Voz e Estilo:** Siga RIGOROSAMENTE o "Tom de Voz Recomendado" e as diretrizes do canal.
5.  **Call to Action (CTA):** O CTA deve ser claro, de baixo atrito e alinhado com o "Objetivo Específico deste Primeiro Contato".
6.  **Concisa e Impactante:** Respeite os limites e a natureza do canal. Vá direto ao ponto, mas com impacto.
7.  **Autenticidade:** A mensagem deve soar genuína e humana, focada em ajudar, não apenas em vender.
8.  **Contexto Brasileiro:** Adapte a linguagem e a abordagem para o mercado brasileiro, valorizando o relacionamento.
9.  **Gancho Inicial:** Utilize ou adapte uma das "Perguntas de Abertura Sugeridas" ou crie um gancho inicial forte e relevante.
10. **Evite Clichês:** Não use frases como "Espero que esteja bem" ou jargões excessivos.

FORMATO DA RESPOSTA:
Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

SCHEMA JSON ESPERADO:
{{
    "subject_line": "string | null - Assunto da mensagem. OBRIGATÓRIO para o canal 'Email' (máx. 50-60 caracteres, conciso e intrigante). Para outros canais (LinkedIn, WhatsApp), DEVE ser null.",
    "message_body": "string - O corpo completo da mensagem personalizada, seguindo todas as instruções e adaptado para o canal '{strategy.primary_channel.value}'.",
    "call_to_action": "string - O call-to-action específico e claro usado na mensagem, alinhado com o 'Objetivo Específico deste Primeiro Contato'.",
    "personalization_elements_used": ["string", ...] - Lista dos principais elementos de personalização que você incorporou na mensagem (ex: 'Nome da empresa', 'Desafio específico X da persona', 'Notícia recente Y sobre a empresa', 'Referência ao objetivo Z da persona'). Mínimo de 2, máximo de 5. Se não for possível identificar elementos específicos, retorne uma lista vazia [].",
    "estimated_read_time_seconds": "integer - Uma estimativa do tempo de leitura da mensagem em segundos (ex: para um corpo de 100 palavras, aproximadamente 30-40 segundos). Deve ser sempre um número inteiro."
}}
"""
    
    def _get_channel_guidance(self, channel: Optional[CommunicationChannel]) -> str: # Handle Optional channel
        """Get channel-specific guidance for message creation"""
        
        # Default guidance if channel is None
        if channel is None:
            return """
DIRETRIZES GERAIS (Canal não especificado):
- Mantenha profissional mas acessível.
- Foque no valor para o destinatário.
- CTA claro e de baixo compromisso.
- Demonstre pesquisa e personalização."""

        if channel == CommunicationChannel.EMAIL:
            return """
DIRETRIZES PARA E-MAIL:
- Assunto: Específico, intrigante, sem spam words (máx 50-60 caracteres).
- Estrutura Sugerida: Saudação personalizada -> Conexão/Contexto (demonstrar pesquisa) -> Proposta de Valor clara e concisa conectada à dor/objetivo -> CTA de baixo atrito -> Assinatura profissional.
- Tamanho Ideal: 80-150 palavras.
- Formato: Profissional, parágrafos curtos, bom uso de quebras de linha.
- CTA: Específico e de baixo compromisso (ex: "Disponível para uma conversa rápida de 10-15 minutos?", "Gostaria de compartilhar um case relevante?")."""
            
        elif channel == CommunicationChannel.LINKEDIN:
            return """
DIRETRIZES PARA LINKEDIN (Mensagem Direta ou Nota de Conexão):
- Assunto: Não aplicável para DMs. Para notas de conexão, seja breve e relevante.
- Estrutura Sugerida: Saudação -> Ponto de conexão relevante (ex: perfil, artigo, conexão mútua) -> Breve proposta de valor -> Pergunta engajadora ou CTA suave.
- Tamanho Ideal: 50-100 palavras (notas de conexão são mais curtas).
- Formato: Conversacional, mas profissional. Evite formalidade excessiva.
- CTA: Convite para conexão (se for nota), ou uma pergunta aberta para iniciar diálogo, ou sugerir um recurso útil. Evite CTAs agressivos de venda imediata."""
            
        elif channel == CommunicationChannel.WHATSAPP: # Assuming WhatsApp might be used in some B2B contexts in Brazil
            return """
DIRETRIZES PARA WHATSAPP (use com extrema cautela e apenas se houver indicação de que é um canal aceitável):
- Assunto: Não aplicável.
- Estrutura Sugerida: Saudação breve e identificação -> Motivo conciso do contato (com muito valor e personalização) -> CTA muito leve (ex: "Posso enviar um áudio rápido explicando melhor?", "Seria útil um link sobre X?").
- Tamanho Ideal: 2-4 frases curtas e diretas. Extremamente conciso.
- Formato: Informal, mas profissional. Use emojis com moderação e apenas se alinhado com o tom da persona.
- CTA: Focado em obter permissão para continuar a conversa ou enviar mais informações. Evite pedir reuniões longas. Priorize o respeito pelo tempo e canal pessoal."""
            
        else: # Fallback for other potential channels or if channel is somehow None
            return """
DIRETRIZES GERAIS:
- Mantenha profissional mas acessível.
- Foque no valor para o destinatário.
- CTA claro e de baixo compromisso.
- Demonstre pesquisa e personalização."""
    
    def _create_personalized_message(self, message_data_dict: Optional[Dict[str, Any]], channel: Optional[CommunicationChannel]) -> PersonalizedMessage: # Handle Optional channel
        """Create PersonalizedMessage from parsed JSON data"""
        
        # Ensure channel has a default if None for safety, though it should be set by lead_with_strategy
        effective_channel = channel if channel is not None else CommunicationChannel.EMAIL

        if not message_data_dict: # Handles if parse_llm_json_response returned None
            self.logger.warning(f"Message data is None, returning fallback message for channel {effective_channel.value}.")
            return self._create_fallback_message(effective_channel)

        try:
            subject_line = message_data_dict.get('subject_line')
            if effective_channel != CommunicationChannel.EMAIL and subject_line is not None:
                self.logger.warning(f"LLM provided subject_line for non-Email channel ({effective_channel.value}). Setting to None.")
                subject_line = None
            
            # Ensure list fields are actually lists
            personalization_elements = message_data_dict.get('personalization_elements', [])
            if not isinstance(personalization_elements, list):
                personalization_elements = [str(personalization_elements)] if personalization_elements else []


            return PersonalizedMessage(
                channel=effective_channel,
                subject_line=subject_line,
                message_body=message_data_dict.get('message_body', 'Mensagem não disponível devido a erro de parsing.'),
                call_to_action=message_data_dict.get('call_to_action', 'Gostaria de explorar como podemos ajudar?'),
                personalization_elements=personalization_elements,
                estimated_read_time=int(message_data_dict.get('estimated_read_time_seconds', 60)), # Ensure int
                ab_variant=None
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create PersonalizedMessage from data: {e}. Data: {message_data_dict}")
            return self._create_fallback_message(effective_channel)
    
    def _create_fallback_message(self, channel: CommunicationChannel) -> PersonalizedMessage:
        """Create a fallback message when parsing fails"""
        self.logger.warning(f"Creating fallback message for channel: {channel.value}")
        
        if channel == CommunicationChannel.EMAIL:
            return PersonalizedMessage(
                channel=channel,
                subject_line="Oportunidade de otimização e crescimento (fallback)",
                message_body="""Olá,\n\nAvaliamos o perfil da sua empresa e identificamos potenciais sinergias com nossas soluções.\n\nAcreditamos que podemos auxiliar na otimização de processos e impulsionar resultados.\n\nGostaria de agendar uma breve conversa para explorarmos isso?\n\nAtenciosamente,\nEquipe de Prospecção (fallback)""",
                call_to_action="Agendar conversa de 15 minutos.",
                personalization_elements=["Setor da empresa (fallback)"],
                estimated_read_time=45
            )
        # Fallback for other channels (LinkedIn, WhatsApp, etc.)
        return PersonalizedMessage(
            channel=channel,
            subject_line=None,
            message_body="""Olá! Identificamos que sua empresa poderia se beneficiar de nossas soluções para otimização de processos. Acredito que uma breve conversa seria muito produtiva. Qual sua disponibilidade?""",
            call_to_action="Agendar breve conversa.",
            personalization_elements=["Setor da empresa (fallback)"],
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
        if message.message_body and message.message_body != 'Mensagem não disponível' and message.message_body != self._create_fallback_message(message.channel).message_body :
            score += 0.15

        return min(round(score, 2), 1.0)

if __name__ == '__main__':
    from loguru import logger
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt snippet:\n{prompt[:600]}...")
            channel = "Email" # Default for mock
            if "Canal Primário Selecionado: LinkedIn" in prompt:
                channel = "LinkedIn"
            elif "Canal Primário Selecionado: WhatsApp" in prompt:
                channel = "WhatsApp"

            subject = "Re: Oportunidade Estratégica para Empresa Exemplo"
            if channel != "Email":
                subject = None

            return json.dumps({
                "subject_line": subject,
                "message_body": f"Este é um corpo de mensagem mock para o canal {channel}, altamente personalizado para Carlos da Empresa Exemplo, focando em desafios de otimização e como Nossas Soluções podem ajudar. Inclui a pergunta de abertura: Como vocês abordam X?",
                "call_to_action": "Vamos conversar por 15 minutos esta semana?",
                "personalization_elements_used": ["Nome da Empresa Exemplo", "Nome da Persona Carlos", "Desafio de Otimização"],
                "estimated_read_time_seconds": 45
            })

    logger.info("Running mock test for MessageCraftingAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    # Provide necessary parameters for BaseAgent init
    agent = MessageCraftingAgent(llm_client=mock_llm)

    # Simulate LeadWithStrategy structure
    from data_models.lead_structures import LeadWithPersona, AnalyzedLead, ValidatedLead, SiteData, GoogleSearchData, LeadAnalysis, PersonaDetails, ApproachStrategy, CommunicationChannel

    mock_site_data = SiteData(url="http://empresaexemplo.com", extracted_text_content="Conteúdo do site da Empresa Exemplo.", google_search_data=GoogleSearchData(title="Empresa Exemplo - Soluções Inovadoras"))
    mock_validated_lead = ValidatedLead(site_data=mock_site_data, extraction_successful=True, cleaned_text_content="Conteúdo limpo.")
    mock_lead_analysis = LeadAnalysis(company_sector="Tecnologia", main_services=["SaaS", "Consultoria"], potential_challenges=["Escalabilidade", "Otimização de custos"], opportunity_fit="Alto")
    mock_analyzed_lead = AnalyzedLead(validated_lead=mock_validated_lead, analysis=mock_lead_analysis, product_service_context="Nossas Soluções Incríveis")
    mock_persona = PersonaDetails(fictional_name="Carlos Mendes", likely_role="Diretor de TI", key_responsibilities=["Gerenciar infraestrutura", "Inovar"], professional_goals=["Reduzir custos", "Aumentar eficiência"], main_challenges=["Integrar novas tecnologias"], motivations=["Resultados mensuráveis"], communication_style="Direto e formal", solution_seeking="Pesquisa online, recomendações")
    mock_lead_with_persona = LeadWithPersona(analyzed_lead=mock_analyzed_lead, persona=mock_persona)
    mock_strategy = ApproachStrategy(
        primary_channel=CommunicationChannel.EMAIL,
        tone_of_voice="Profissional e direto",
        key_value_propositions=["Redução de custos em 20%", "Aumento de produtividade"],
        talking_points=["Case de sucesso XPTO", "Integração facilitada"],
        opening_questions=["Como vocês lidam com o desafio X atualmente?"],
        first_interaction_goal="Agendar uma call de 15 minutos",
        potential_objections={"Preço": "Nosso ROI compensa."},
        follow_up_strategy="Enviar case study após 2 dias se não houver resposta."
    )

    input_data = LeadWithStrategy(lead_with_persona=mock_lead_with_persona, strategy=mock_strategy)
    output = agent.process(input_data)

    logger.info(f"Final Package Lead ID: {output.lead_id}")
    logger.info(f"Message Channel: {output.personalized_message.channel.value}")
    logger.info(f"Subject: {output.personalized_message.subject_line}")
    logger.info(f"Body: \n{output.personalized_message.message_body}")
    logger.info(f"CTA: {output.personalized_message.call_to_action}")
    logger.info(f"Personalization: {output.personalized_message.personalization_elements}")
    logger.info(f"Read Time (s): {output.personalized_message.estimated_read_time}")
    logger.info(f"Confidence Score: {output.confidence_score}")
    if output.personalized_message.error_message: # Assuming error_message might be on PersonalizedMessage if parsing failed for it
        logger.error(f"Error in message: {output.personalized_message.error_message}")

    assert output.personalized_message.error_message is None
    assert output.personalized_message.channel == CommunicationChannel.EMAIL
    assert "Empresa Exemplo" in output.personalized_message.message_body
    assert "Carlos" in output.personalized_message.message_body
    assert "Nossas Soluções Incríveis" not in output.personalized_message.message_body # It should use the context, not literally state "Nossas Soluções Incríveis"
    assert output.confidence_score > 0.3 # Check it's a reasonable score

    logger.info("\nMock test for MessageCraftingAgent completed successfully.")
```
