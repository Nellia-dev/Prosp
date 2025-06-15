"""
Persona Creation Agent for Nellia Prospector
Creates detailed decision-maker personas for analyzed leads.
"""

from typing import Optional, List
from datetime import datetime
from loguru import logger
import json # For mock test
from pydantic import BaseModel, Field # Ensure Field is imported

from data_models.lead_structures import (
    AnalyzedLead, 
    LeadWithPersona
    # PersonaDetails will be defined/redefined in this file as per subtask
)
from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# --- Updated Pydantic Model for PersonaDetails ---
class PersonaDetails(BaseModel):
    fictional_name: str = "Nome não definido"
    likely_role: str = "Cargo não definido"
    key_responsibilities: List[str] = Field(default_factory=list)
    professional_goals: List[str] = Field(default_factory=list)
    main_challenges_needs: List[str] = Field(default_factory=list) # Renamed from main_challenges
    motivations_drivers: List[str] = Field(default_factory=list) # Renamed from motivations
    preferred_communication_channels: List[str] = Field(default_factory=list) # New field
    information_sources: List[str] = Field(default_factory=list) # New field, replaces solution_seeking
    decision_making_process_summary: str = "Processo de decisão não especificado." # Renamed from decision_making_process
    potential_hooks_for_engagement: List[str] = Field(default_factory=list) # New field
    # communication_style and solution_seeking from old model are now covered by new fields or implicitly.

class PersonaCreationAgent(BaseAgent[AnalyzedLead, LeadWithPersona]):
    """Agent responsible for creating decision-maker personas for leads"""
    
    def __init__(self, llm_client: Optional[LLMClientBase] = None, **kwargs): # Added **kwargs
        super().__init__(
            name="PersonaCreationAgent",
            description="Creates detailed decision-maker personas for B2B leads",
            llm_client=llm_client,
            **kwargs # Pass **kwargs
        )
        
    def process(self, analyzed_lead: AnalyzedLead) -> LeadWithPersona:
        """
        Create a detailed persona for the analyzed lead
        
        Args:
            analyzed_lead: AnalyzedLead with company analysis
            
        Returns:
            LeadWithPersona with persona details
        """
        logger.info(f"🎭 PERSONA CREATION AGENT STARTING for: {analyzed_lead.validated_lead.site_data.url}")
        
        prompt = self._build_persona_prompt(analyzed_lead)
        
        llm_response_str = self.generate_llm_response(prompt)
        
        persona_details_dict = self.parse_llm_json_response(llm_response_str, None) # Expects dict
        
        if persona_details_dict is None or persona_details_dict.get("error_message"):
            logger.warning(f"⚠️ Persona creation failed for {analyzed_lead.validated_lead.site_data.url} due to LLM error or JSON parsing. Using fallback. Error: {persona_details_dict.get('error_message', 'Unknown parsing error') if persona_details_dict else 'LLM response was None'}")
            persona = self._create_fallback_persona_details()
        else:
            persona = self._create_persona_details(persona_details_dict)
        
        result = LeadWithPersona(
            analyzed_lead=analyzed_lead,
            persona=persona,
            persona_creation_timestamp=datetime.now()
        )
        
        logger.info(f"✅ Persona created for {analyzed_lead.validated_lead.site_data.url}: {persona.fictional_name} ({persona.likely_role})")
        return result

    def _join_list_or_na(self, data_list: Optional[List[str]], default_str="N/A") -> str:
        """Helper to join list elements into a string or return default."""
        if data_list and isinstance(data_list, list) and len(data_list) > 0:
            return ', '.join(filter(None, data_list))
        return default_str
    
    def _build_persona_prompt(self, analyzed_lead: AnalyzedLead) -> str:
        """Build the prompt for persona creation - REFINED"""
        
        analysis = analyzed_lead.analysis
        company_info_dict = { # Using a dict for easier formatting and default handling
            "url": str(analyzed_lead.validated_lead.site_data.url),
            "sector": analysis.company_sector or "Não Especificado",
            "services": self._join_list_or_na(analysis.main_services, "Não Especificados"),
            "challenges": self._join_list_or_na(analysis.potential_challenges, "Não Especificados"),
            "company_size": analysis.company_size_estimate or "Não Determinado",
            "culture": analysis.company_culture_values or "Não Determinada",
            "diagnosis": analysis.general_diagnosis or "Diagnóstico não disponível"
        }
        
        # Refined prompt template
        return f"""Você é um Estrategista de Marketing B2B e especialista em criação de personas, com foco no mercado brasileiro.
Sua tarefa é criar um perfil de persona detalhado e acionável para um tomador de decisão chave na empresa analisada, com base nas informações fornecidas.

INFORMAÇÕES DA EMPRESA ANALISADA:
- URL: {company_info_dict['url']}
- Setor: {company_info_dict['sector']}
- Principais Serviços/Produtos: {company_info_dict['services']}
- Desafios Identificados da Empresa: {company_info_dict['challenges']}
- Tamanho Estimado: {company_info_dict['company_size']}
- Cultura Organizacional (inferida): {company_info_dict['culture']}
- Diagnóstico Geral da Empresa: {company_info_dict['diagnosis']}

CONSIDERAÇÕES SOBRE O MERCADO BRASILEIRO (para guiar a criação da persona):
- Hierarquia e formalidade podem ser importantes nas relações empresariais.
- Decisões B2B frequentemente envolvem múltiplos stakeholders e um processo consultivo.
- Construção de relacionamento e confiança (confiança) são cruciais antes de fechar negócios.
- Comunicação tende a ser direta, mas sempre cordial e respeitosa.
- Profissionais valorizam fornecedores que demonstram entender seus desafios específicos e o contexto local.

INSTRUÇÕES PARA CRIAÇÃO DA PERSONA:
Crie uma persona específica para um tomador de decisão chave relevante para a venda de soluções B2B para esta empresa.
A persona deve ser realista para o contexto brasileiro e baseada nas informações da empresa (setor, tamanho, desafios).

Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

SCHEMA JSON ESPERADO PARA A PERSONA:
{{
  "fictional_name": "string - Nome fictício COMPLETO e realista para um profissional brasileiro (ex: 'João Carlos Almeida', 'Sofia Ribeiro Lima').",
  "likely_role": "string - Cargo/função provável do decisor na estrutura da empresa (ex: 'Diretor de TI', 'Gerente de Marketing e Vendas', 'Head de Operações'). Considere o tamanho da empresa.",
  "key_responsibilities": ["string", ...], // Lista de 2-4 responsabilidades chave do cargo. Lista vazia [] se não inferível.
  "professional_goals": ["string", ...], // Lista de 2-3 objetivos profissionais que esta persona provavelmente possui. Lista vazia [] se não inferível.
  "main_challenges_needs": ["string", ...], // Lista de 2-3 desafios principais ou necessidades que esta persona enfrenta em seu cargo, idealmente conectadas aos desafios da empresa. Lista vazia [] se não inferível.
  "motivations_drivers": ["string", ...], // Lista de 2-3 fatores que motivam esta persona e impulsionam suas decisões profissionais (ex: 'Reconhecimento no mercado', 'Resultados mensuráveis e ROI', 'Inovação tecnológica', 'Estabilidade e segurança'). Lista vazia [] se não inferível.
  "preferred_communication_channels": ["string", ...], // Lista dos canais de comunicação profissional preferidos por esta persona (ex: 'Email formal', 'LinkedIn (mensagens e networking)', 'WhatsApp para contatos estabelecidos', 'Videoconferências agendadas'). Lista vazia [] se não inferível.
  "information_sources": ["string", ...], // Lista de fontes onde esta persona provavelmente busca informações para se manter atualizada e encontrar soluções B2B (ex: 'Blogs de especialistas do setor', 'Eventos e feiras de negócios', 'Redes de contatos profissionais', 'Consultorias especializadas', 'Publicações de mercado'). Lista vazia [] se não inferível.
  "decision_making_process_summary": "string - Breve resumo de como esta persona provavelmente toma decisões de compra B2B (ex: 'Analisa dados e ROI cuidadosamente, busca consenso com a equipe técnica, valoriza referências e cases de sucesso, pode precisar de aprovação superior para grandes investimentos.'). Se não inferível, use 'Processo de decisão não claramente inferível'.",
  "potential_hooks_for_engagement": ["string", ...] // Lista de 2-3 'ganchos' ou temas potenciais que poderiam despertar o interesse desta persona para uma conversa inicial, baseados em seus desafios, objetivos e no que a empresa analisada oferece. Lista vazia [] se não inferível.
}}
"""
    
    def _create_persona_details(self, persona_data: Optional[Dict[str, Any]]) -> PersonaDetails: # persona_data can be None
        """Create PersonaDetails from parsed JSON data"""
        if not persona_data: # Handles if parse_llm_json_response returned None or if there was an error before
            self.logger.warning(f"Persona data is None, returning fallback persona details for {self.name}")
            return self._create_fallback_persona_details()

        try:
            # Ensure lists are correctly handled if LLM returns single string or null
            def _ensure_list(value: Any) -> List[str]:
                if isinstance(value, list):
                    return [str(item) for item in value if item is not None]
                if isinstance(value, str):
                    return [value] if value.strip() else []
                return []

            return PersonaDetails(
                fictional_name=persona_data.get('fictional_name', 'Nome não fornecido'),
                likely_role=persona_data.get('likely_role', 'Cargo não fornecido'),
                key_responsibilities=_ensure_list(persona_data.get('key_responsibilities')),
                professional_goals=_ensure_list(persona_data.get('professional_goals')),
                main_challenges_needs=_ensure_list(persona_data.get('main_challenges_needs')),
                motivations_drivers=_ensure_list(persona_data.get('motivations_drivers')),
                preferred_communication_channels=_ensure_list(persona_data.get('preferred_communication_channels')),
                information_sources=_ensure_list(persona_data.get('information_sources')),
                decision_making_process_summary=persona_data.get('decision_making_process_summary', 'Processo de decisão não especificado.'),
                potential_hooks_for_engagement=_ensure_list(persona_data.get('potential_hooks_for_engagement'))
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to create PersonaDetails from data for {self.name}: {e}. Data: {persona_data}")
            return self._create_fallback_persona_details()

    def _create_fallback_persona_details(self) -> PersonaDetails:
        """Creates a fallback PersonaDetails object."""
        return PersonaDetails(
            fictional_name="Alex Silva (Fallback)",
            likely_role="Gerente de Nível Sênior (Fallback)",
            key_responsibilities=["Gerenciamento de equipe", "Resultados do departamento"],
            professional_goals=["Atingir metas", "Inovar na área"],
            main_challenges_needs=["Falta de tempo", "Recursos limitados"],
            motivations_drivers=["Eficiência", "Reconhecimento"],
            preferred_communication_channels=["Email"],
            information_sources=["Webinars", "Artigos de indústria"],
            decision_making_process_summary="Baseado em dados e ROI, consulta equipe.",
            potential_hooks_for_engagement=["Como otimizar X?", "Desafios com Y?"]
        )

if __name__ == '__main__':
    from loguru import logger
    import sys
    # Assuming data_models.lead_structures is in the same parent directory for standalone testing
    # This might need adjustment based on actual project structure
    sys.path.append(json.os.path.join(json.os.path.dirname(__file__), '../..'))
    from data_models.lead_structures import AnalyzedLead, ValidatedLead, SiteData, GoogleSearchData, LeadAnalysis

    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt snippet:\n{prompt[:600]}...")
            # Simulate LLM returning valid JSON based on the refined prompt and new model
            return json.dumps({
                "fictional_name": "Renata Oliveira",
                "likely_role": "Diretora de Marketing",
                "key_responsibilities": ["Definir estratégia de marketing digital", "Gerenciar orçamento de marketing", "Liderar equipe de marketing"],
                "professional_goals": ["Aumentar market share da Empresa Exemplo", "Lançar campanhas de sucesso", "Ser reconhecida como líder inovadora"],
                "main_challenges_needs": ["Justificar ROI de campanhas de marketing", "Manter-se atualizada com novas tecnologias de marketing", "Engajar audiência B2B de forma eficaz"],
                "motivations_drivers": ["Resultados mensuráveis (KPIs)", "Inovação e criatividade", "Crescimento da marca"],
                "preferred_communication_channels": ["Email profissional", "LinkedIn para networking e conteúdo", "Videoconferências agendadas"],
                "information_sources": ["Blogs de marketing digital (ex: HubSpot, RD Station)", "Eventos do setor (digitais e presenciais)", "Webinars de especialistas", "Cases de sucesso de outras empresas"],
                "decision_making_process_summary": "Analisa dados de performance, busca soluções com bom custo-benefício e que demonstrem ROI claro. Valoriza a opinião de sua equipe e consulta o CMO/CEO para decisões de maior impacto financeiro.",
                "potential_hooks_for_engagement": ["Como a Empresa Exemplo está medindo o ROI das suas atuais estratégias de conteúdo?", "Quais os maiores desafios para engajar o público B2B no setor de TI atualmente?", "Considerando a expansão, como pretendem adaptar a comunicação de marketing para novos mercados?"]
            })

    logger.info("Running mock test for PersonaCreationAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = PersonaCreationAgent(llm_client=mock_llm)

    # Simulate AnalyzedLead input
    mock_site_data = SiteData(url="http://empresaexemplo.com.br", extracted_text_content="Conteúdo do site da Empresa Exemplo sobre soluções de TI.", google_search_data=GoogleSearchData(title="Empresa Exemplo - Líder em TI"))
    mock_validated_lead = ValidatedLead(site_data=mock_site_data, extraction_successful=True, cleaned_text_content="Conteúdo limpo sobre TI e SaaS.")
    mock_lead_analysis = LeadAnalysis(
        company_sector="Tecnologia da Informação (SaaS)",
        main_services=["Desenvolvimento de Software Customizado", "Consultoria em Nuvem"],
        potential_challenges=["Escalar atendimento ao cliente", "Manter inovação frente à concorrência"],
        company_size_estimate="Médio Porte (50-200 funcionários)",
        company_culture_values="Foco no cliente, Inovação Contínua",
        general_diagnosis="Empresa sólida em TI, com desafios de crescimento e necessidade de otimizar marketing digital para novos produtos.",
        relevance_score=0.8,
        opportunity_fit="Nossas soluções de automação de marketing podem ajudar a escalar o engajamento e a qualificação de leads para seus novos produtos."
    )
    test_analyzed_lead = AnalyzedLead(validated_lead=mock_validated_lead, analysis=mock_lead_analysis, product_service_context="Nossas Soluções de Automação de Marketing")

    output = agent.process(test_analyzed_lead)

    if output.persona.error_message: # Assuming error would be on persona if it's a fallback
        logger.error(f"Error: {output.persona.error_message}")
    else:
        logger.success("PersonaCreationAgent processed successfully.")
        logger.info(f"Persona Fictional Name: {output.persona.fictional_name}")
        logger.info(f"Likely Role: {output.persona.likely_role}")
        logger.info(f"Key Responsibilities: {output.persona.key_responsibilities}")
        logger.info(f"Professional Goals: {output.persona.professional_goals}")
        logger.info(f"Main Challenges/Needs: {output.persona.main_challenges_needs}")
        logger.info(f"Motivations/Drivers: {output.persona.motivations_drivers}")
        logger.info(f"Preferred Channels: {output.persona.preferred_communication_channels}")
        logger.info(f"Information Sources: {output.persona.information_sources}")
        logger.info(f"Decision Making Summary: {output.persona.decision_making_process_summary}")
        logger.info(f"Potential Hooks: {output.persona.potential_hooks_for_engagement}")

    assert output.persona.fictional_name == "Renata Oliveira"
    assert "Diretora de Marketing" in output.persona.likely_role
    assert len(output.persona.key_responsibilities) > 0
    assert len(output.persona.main_challenges_needs) > 0
    assert "ROI" in output.persona.decision_making_process_summary

    logger.info("\nMock test for PersonaCreationAgent completed successfully.")

```
