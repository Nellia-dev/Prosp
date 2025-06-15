from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import json # Ensure json is imported

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class InternalBriefingSummaryInput(BaseModel):
    all_lead_data: Dict[str, Any] # Dictionary holding all previously generated data

# --- Updated Pydantic Output Models (as per subtask refinement) ---
class LeadProfileHighlights(BaseModel):
    company_overview: str = "Visão geral da empresa não fornecida."
    key_persona_traits: str = "Traços chave da persona não fornecidos."
    critical_pain_points: List[str] = Field(default_factory=list)

class StrategicApproachSummary(BaseModel):
    main_objective: str = "Objetivo principal não fornecido."
    core_value_proposition: str = "Proposição de valor central não fornecida."
    suggested_communication_channels: List[str] = Field(default_factory=list)

class EngagementPlanOverview(BaseModel):
    first_step_action: str = "Primeiro passo não fornecido."
    key_talking_points_initial: List[str] = Field(default_factory=list)

class ObjectionResponsePair(BaseModel):
    objection: str = "Objeção não especificada."
    suggested_response: str = "Resposta não sugerida."

class InternalBriefingSummaryOutput(BaseModel):
    executive_summary: str = "Resumo executivo não fornecido."
    lead_profile_highlights: LeadProfileHighlights = Field(default_factory=LeadProfileHighlights)
    strategic_approach_summary: StrategicApproachSummary = Field(default_factory=StrategicApproachSummary)
    engagement_plan_overview: EngagementPlanOverview = Field(default_factory=EngagementPlanOverview)
    potential_objections_and_responses: List[ObjectionResponsePair] = Field(default_factory=list)
    key_discussion_points_for_sales_exec: List[str] = Field(default_factory=list)
    suggested_next_steps_internal: List[str] = Field(default_factory=list)
    final_recommendation_notes: Optional[str] = "Nenhuma nota final específica."
    error_message: Optional[str] = None
# --- End of Updated Pydantic Output Models ---

class InternalBriefingSummaryAgent(BaseAgent[InternalBriefingSummaryInput, InternalBriefingSummaryOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        if not isinstance(text, str):
            text = json.dumps(text, ensure_ascii=False) # Convert dicts/lists to JSON string if they appear
        return text[:max_chars]

    def _format_dict_for_prompt(self, data: Dict[str, Any], max_total_chars: int) -> str:
        """Formats the dictionary into a string, truncating individual long values."""
        formatted_parts = []

        # Prioritize certain keys for more characters if needed, or simply divide
        # For now, simple division, but a more sophisticated budgeting could be implemented
        num_items = len(data) if len(data) > 0 else 1
        # Give a bit more to complex fields if they exist by checking keys
        # This is a heuristic
        complex_field_keys = ['lead_analysis', 'persona_profile', 'deepened_pain_points',
                              'final_action_plan_text', 'detailed_approach_plan', 'customized_value_propositions_text']

        total_chars_used = 0

        # First pass for complex fields with potentially larger budget
        temp_complex_parts = {}
        for key, value in data.items():
            if key in complex_field_keys:
                str_value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
                # Allocate more chars for these, e.g., 15% of total budget each if all present
                max_chars_per_item = int(max_total_chars * 0.15)
                truncated_value = self._truncate_text(str_value, max_chars_per_item)
                temp_complex_parts[key] = f"--- {key.replace('_', ' ').title()} ---\n{truncated_value}\n\n"
                total_chars_used += len(temp_complex_parts[key])

        remaining_chars = max_total_chars - total_chars_used
        non_complex_keys = [k for k in data.keys() if k not in complex_field_keys]
        num_non_complex_items = len(non_complex_keys) if non_complex_keys else 1
        max_chars_per_non_complex_item = remaining_chars // num_non_complex_items if remaining_chars > 0 else 50 # Small default

        for key in non_complex_keys:
            value = data[key]
            str_value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
            truncated_value = self._truncate_text(str_value, max_chars_per_non_complex_item)
            formatted_parts.append(f"--- {key.replace('_', ' ').title()} ---\n{truncated_value}\n\n")

        # Add complex parts to the final list
        for key in complex_field_keys: # Maintain order if possible or define specific order
            if key in temp_complex_parts:
                formatted_parts.append(temp_complex_parts[key])

        return "".join(formatted_parts)


    def process(self, input_data: InternalBriefingSummaryInput) -> InternalBriefingSummaryOutput:
        error_message = None
        self.logger.info(f"📝 INTERNAL BRIEFING SUMMARY AGENT STARTING for lead data containing keys: {list(input_data.all_lead_data.keys())}")

        try:
            # Prepare the all_lead_data for the prompt by formatting and truncating
            # Reserve ample space for the prompt instructions and JSON structure definition
            prompt_instructions_overhead = 4000
            lead_data_for_prompt_str = self._format_dict_for_prompt(
                input_data.all_lead_data,
                GEMINI_TEXT_INPUT_TRUNCATE_CHARS - prompt_instructions_overhead
            )

            # Refined prompt_template based on the new Pydantic models
            prompt_template = """
                Você é um Gerente de Sales Enablement e Estrategista de Contas Sênior, expert em criar briefings internos concisos, estratégicos e acionáveis para preparar executivos de vendas B2B para interações de alto impacto, especialmente no mercado brasileiro.
                Sua tarefa é analisar o extenso compilado de dados sobre um lead e sintetizá-lo em um "Briefing Interno Estratégico" em formato JSON.

                DADOS COMPLETOS DO LEAD (organizados por seção, extraídos de análises anteriores):
                \"\"\"
                {all_lead_data_formatted_str}
                \"\"\"

                INSTRUÇÕES PARA CRIAÇÃO DO BRIEFING:
                Com base em TODOS os dados fornecidos acima, gere um briefing que arme o executivo de vendas com o conhecimento essencial e um plano claro.
                Seja conciso em cada campo, mas garanta que as informações críticas sejam destacadas.
                Adapte a linguagem e as sugestões para o contexto de negócios brasileiro, se aplicável com base nos dados.

                FORMATO DA RESPOSTA:
                Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

                SCHEMA JSON ESPERADO:
                {{
                  "executive_summary": "string - Um resumo executivo do lead e da oportunidade em 2-3 frases impactantes, destacando a principal razão para o engajamento.",
                  "lead_profile_highlights": {{
                    "company_overview": "string - Breve visão geral da empresa do lead (setor, tamanho aproximado, principal negócio/produto).",
                    "key_persona_traits": "string - Principais características da persona alvo (cargo provável, responsabilidades chave, motivações principais, estilo de comunicação preferido).",
                    "critical_pain_points": ["string", ...] // Lista dos 2-3 pontos de dor mais críticos da persona/empresa que nossa solução parece poder resolver, com base na análise. Lista vazia [] se não claro.
                  }},
                  "strategic_approach_summary": {{
                    "main_objective": "string - O objetivo principal e mais estratégico para esta abordagem específica com o lead.",
                    "core_value_proposition": "string - A proposição de valor central e mais ressonante para este lead, conectando nossa solução às suas dores/objetivos de forma concisa.",
                    "suggested_communication_channels": ["string", ...] // Lista dos 1-2 canais de comunicação mais promissores para esta persona (ex: 'Email', 'LinkedIn'). Lista vazia [] se não claro.
                  }},
                  "engagement_plan_overview": {{
                     "first_step_action": "string - Ação concreta e descrição do primeiro passo recomendado no plano de contato (ex: 'Enviar email personalizado focando em [dor X] com CTA para call de 15 min').",
                     "key_talking_points_initial": ["string", ...] // Lista de 2-3 pontos de discussão chave para a interação inicial, derivados da proposta de valor e dores. Lista vazia [] se não houver.
                  }},
                  "potential_objections_and_responses": [ // Lista de 1-2 objeções mais prováveis e respostas sugeridas. Lista vazia [] se não houver objeções óbvias.
                    {{
                      "objection": "string - Objeção potencial (ex: 'Já temos uma solução similar', 'Não temos orçamento no momento').",
                      "suggested_response": "string - Resposta concisa e estratégica sugerida para a objeção."
                    }}
                  ],
                  "key_discussion_points_for_sales_exec": ["string", ...], // Lista de 2-3 perguntas ou pontos cruciais que o executivo de vendas deve abordar ou investigar durante as conversas para aprofundar o entendimento. Lista vazia [] se não houver.
                  "suggested_next_steps_internal": ["string", ...], // Lista de 1-2 próximos passos internos para a equipe de vendas ANTES do contato ou como PREPARAÇÃO (ex: 'Pesquisar conexões em comum com o decisor no LinkedIn', 'Revisar o case de sucesso da Empresa Y'). Lista vazia [] se não houver.
                  "final_recommendation_notes": "string | null" // Quaisquer notas finais importantes, recomendações estratégicas adicionais ou alertas para a equipe de vendas. Use null se não houver.
                }}
            """

            formatted_prompt = prompt_template.format(
                all_lead_data_formatted_str=lead_data_for_prompt_str
            )
            self.logger.debug(f"Prompt for {self.name} (length: {len(formatted_prompt)}):\n{formatted_prompt[:1000]}...")

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                self.logger.error(f"❌ LLM call returned no response for {self.name}")
                return InternalBriefingSummaryOutput(error_message="LLM call returned no response.")

            self.logger.debug(f"LLM response received for {self.name} (length: {len(llm_response_str)}). Attempting to parse.")
            parsed_output = self.parse_llm_json_response(llm_response_str, InternalBriefingSummaryOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"⚠️ {self.name} JSON parsing failed or model validation issue. Error: {parsed_output.error_message}. Raw response snippet: {llm_response_str[:500]}")
                 return parsed_output
            
            self.logger.info(f"✅ Internal briefing summary successfully processed for lead data associated with: {input_data.all_lead_data.get('company_name', 'N/A')}")
            return parsed_output

        except Exception as e:
            self.logger.error(f"❌ An unexpected error occurred in {self.name}: {e}", exc_info=True)
            return InternalBriefingSummaryOutput(error_message=f"An unexpected error occurred: {str(e)}")

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
            # Simulate LLM returning valid JSON based on the refined prompt and new model
            return json.dumps({
                "executive_summary": "Empresa Exemplo (TI, Médio Porte) apresenta alta sinergia com Nossas Soluções de IA, especialmente devido à sua expansão LATAM e foco em otimizar operações. O Diretor de Operações, Carlos Mendes, é o contato chave.",
                "lead_profile_highlights": {
                    "company_overview": "Empresa Exemplo é uma empresa de TI de médio porte, focada em SaaS para gestão de projetos, atualmente expandindo para a América Latina. Busca modernizar sua tecnologia.",
                    "key_persona_traits": "Carlos Mendes (Dir. Operações) valoriza ROI, eficiência e integração fácil. Comunica-se formalmente via email/LinkedIn.",
                    "critical_pain_points": ["Escalabilidade de processos manuais de QA durante expansão.", "Necessidade de modernização tecnológica sem disrupção."]
                },
                "strategic_approach_summary": {
                    "main_objective": "Agendar uma conversa exploratória de 20 minutos com Carlos Mendes para discutir otimização de QA e DevOps com IA no contexto da expansão LATAM.",
                    "core_value_proposition": "Nossas Soluções de IA para Automação de QA e DevOps podem ajudar a Empresa Exemplo a escalar suas operações LATAM eficientemente, garantindo qualidade e velocidade sem sobrecarregar a equipe.",
                    "suggested_communication_channels": ["Email Personalizado", "LinkedIn"]
                },
                "engagement_plan_overview": {
                    "first_step_action": "Enviar email personalizado para Carlos Mendes focado nos desafios da expansão e otimização de QA, com CTA para uma call de 20 min.",
                    "key_talking_points_initial": ["Impacto da expansão LATAM na eficiência de QA", "Benefícios da automação de QA com IA", "Cases de sucesso similares"]
                },
                "potential_objections_and_responses": [
                    {
                        "objection": "Já temos uma solução de QA ou estamos desenvolvendo internamente.",
                        "suggested_response": "Entendo. Muitas empresas buscam complementar suas iniciativas atuais para acelerar resultados. Nossa IA pode se integrar ou oferecer uma nova perspectiva para gargalos específicos. Poderíamos explorar como?"
                    },
                    {
                        "objection": "Não temos orçamento para novas ferramentas agora.",
                        "suggested_response": "Compreensível, especialmente durante uma expansão. Nosso foco é justamente em otimizar custos e gerar ROI. Uma conversa rápida poderia nos ajudar a identificar o potencial de economia para a Empresa Exemplo?"
                    }
                ],
                "key_discussion_points_for_sales_exec": [
                    "Quais são os maiores gargalos atuais nos ciclos de QA da Empresa Exemplo com a expansão?",
                    "Como a Empresa Exemplo mede o sucesso da eficiência operacional em DevOps?",
                    "Quais são as prioridades de Carlos Mendes para os próximos 6 meses em relação à tecnologia e operações?"
                ],
                "suggested_next_steps_internal": [
                    "Pesquisar conexões de 2º grau com Carlos Mendes no LinkedIn.",
                    "Revisar o case de sucesso da 'GlobalTech' que teve expansão similar."
                ],
                "final_recommendation_notes": "Focar a abordagem no impacto da expansão e na experiência de Carlos com otimização. Ser consultivo e focado em ROI."
            })

    logger.info("Running mock test for InternalBriefingSummaryAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = InternalBriefingSummaryAgent(
        name="TestInternalBriefingAgent",
        description="Test Agent for Internal Briefing Summary",
        llm_client=mock_llm
    )

    test_all_lead_data = {
        "company_name": "Empresa Exemplo",
        "lead_url": "http://www.empresaexemplo.com.br",
        "product_service_context": "Nossas Soluções de IA para Automação de QA e DevOps", # User's product
        "lead_analysis": {"company_sector": "TI", "company_size_estimate": "Médio Porte", "main_services": ["SaaS para gestão de projetos"], "potential_challenges": ["escalabilidade", "modernização tecnológica"], "general_diagnosis": "Empresa em expansão LATAM."},
        "persona_profile": {"fictional_name": "Carlos Mendes", "likely_role": "Diretor de Operações", "key_responsibilities": ["eficiência operacional"], "motivations": ["ROI claro", "integração fácil"]},
        "deepened_pain_points": {"primary_pain_category": "Eficiência Operacional em Expansão", "detailed_pain_points": [{"pain": "Processos manuais em QA", "impact": "Atrasos"}]},
        "final_action_plan_text": {"recommended_strategy_name": "Eficiência Consultiva", "main_call_to_action": "Agendar call de 20 min"},
        "customized_value_propositions_text": [{"proposition_title": "Escalabilidade com IA", "detailed_explanation": "Ajuda na expansão LATAM."}],
        "objection_handling_strategies": [{"objection": "Custo", "response_strategy": "Focar em ROI."}],
        "detailed_approach_plan": {"main_objective": "Agendar call", "contact_sequence": [{"step_number": 1, "channel": "Email", "objective": "Introdução"}]},
        "personalized_message_draft": {"crafted_message_channel": "Email", "crafted_message_subject": "Otimizando QA na Empresa Exemplo", "crafted_message_body": "Olá Carlos..."},
        # Simplified for brevity, a real one would have more fields from EnhancedStrategy
    }

    input_data = InternalBriefingSummaryInput(all_lead_data=test_all_lead_data)
    output = agent.process(input_data)

    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("InternalBriefingSummaryAgent processed successfully.")
        logger.info(f"Executive Summary: {output.executive_summary}")
        logger.info(f"Lead Overview Title: {output.lead_profile_highlights.company_overview}") # Accessing nested field
        logger.info(f"Strategic Approach Objective: {output.strategic_approach_summary.main_objective}")
        assert "Empresa Exemplo" in output.executive_summary
        assert "Carlos Mendes" in output.lead_profile_highlights.key_persona_traits
        assert len(output.potential_objections_and_responses) > 0
        assert output.final_recommendation_notes is not None

    assert output.error_message is None
    logger.info("\nMock test for InternalBriefingSummaryAgent completed successfully.")

```
