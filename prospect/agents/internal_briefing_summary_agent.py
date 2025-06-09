from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000 # Adjusted for potentially large combined input

class InternalBriefingSummaryInput(BaseModel):
    all_lead_data: Dict[str, Any] # Dictionary holding all previously generated data

# Suggestion for a more structured output model
class InternalBriefingSection(BaseModel):
    title: str
    content: str # Could also be List[str] if more granularity is needed

class InternalBriefingSummaryOutput(BaseModel):
    executive_summary: str = "Não especificado"
    lead_overview: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Visão Geral do Lead", content=""))
    persona_profile_summary: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Perfil da Persona", content=""))
    pain_points_and_needs: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Dores e Necessidades", content=""))
    buying_triggers_opportunity: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Gatilhos de Compra e Oportunidade", content=""))
    lead_qualification_summary: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Qualificação do Lead", content=""))
    approach_strategy_summary: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Estratégia de Abordagem", content=""))
    custom_value_proposition_summary: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Proposta de Valor Customizada", content=""))
    potential_objections_summary: InternalBriefingSection = Field(default_factory=lambda: InternalBriefingSection(title="Objeções Potenciais", content=""))
    recommended_next_step: str = "Não especificado"
    error_message: Optional[str] = None

class InternalBriefingSummaryAgent(BaseAgent[InternalBriefingSummaryInput, InternalBriefingSummaryOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        if not isinstance(text, str): # Handle cases where a dict value might not be a string
            text = str(text)
        return text[:max_chars]

    def _format_dict_for_prompt(self, data: Dict[str, Any], max_total_chars: int) -> str:
        """Formats the dictionary into a string, truncating individual long values."""
        formatted_string = ""
        # Calculate max chars per item roughly, this is a simplification
        # A more robust approach might involve iterative truncation or sizing
        num_items = len(data) if len(data) > 0 else 1
        max_chars_per_item = max_total_chars // num_items

        for key, value in data.items():
            # Convert non-string values to string and truncate
            str_value = str(value)
            truncated_value = self._truncate_text(str_value, max_chars_per_item)
            formatted_string += f"--- {key.replace('_', ' ').title()} ---\n{truncated_value}\n\n"
        return formatted_string


    def process(self, input_data: InternalBriefingSummaryInput) -> InternalBriefingSummaryOutput:
        briefing_summary_text = ""
        error_message = None

        try:
            # Prepare the all_lead_data for the prompt by formatting and truncating
            # The cw.py version directly interpolates dictionary values into a very long f-string.
            # Here, we'll create a string representation of the key data points.
            # The prompt will guide the LLM on how to interpret this structured string.

            lead_data_for_prompt = self._format_dict_for_prompt(input_data.all_lead_data, GEMINI_TEXT_INPUT_TRUNCATE_CHARS - 1000) # Reserve space for prompt instructions

            prompt_template = """
                Você é um Especialista em Comunicação Interna de Vendas, responsável por criar briefings concisos e acionáveis para a equipe de vendas.
                Seu objetivo é sumarizar todas as informações coletadas sobre um lead em um briefing interno compreensível.

                DADOS COMPLETOS DO LEAD (organizados por seção):
                {all_lead_data_formatted_str}

                INSTRUÇÕES:
                Com base em TODOS os dados fornecidos acima (`all_lead_data_formatted_str`), crie um "Briefing Interno do Lead" conciso e acionável.
                Estruture a resposta como um objeto JSON.

                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "executive_summary": "Sumário executivo do lead e da oportunidade (string).",
                    "lead_overview": {{
                        "title": "Visão Geral do Lead",
                        "content": "Empresa, URL, descrição, produto/serviço oferecido a eles (string)."
                    }},
                    "persona_profile_summary": {{
                        "title": "Perfil da Persona",
                        "content": "Nome fictício, cargo, responsabilidades, motivações (string)."
                    }},
                    "pain_points_and_needs": {{
                        "title": "Dores e Necessidades Principais",
                        "content": "Resumo dos pontos de dor críticos e como nosso produto/serviço se conecta (string)."
                    }},
                    "buying_triggers_opportunity": {{
                        "title": "Gatilhos de Compra e Oportunidade",
                        "content": "Eventos ou sinais que indicam necessidade (expansão, novo líder, etc.) (string)."
                    }},
                    "lead_qualification_summary": {{
                        "title": "Qualificação do Lead",
                        "content": "Avaliação do potencial (Alto, Médio, Baixo) e justificativa (string)."
                    }},
                    "approach_strategy_summary": {{
                        "title": "Estratégia de Abordagem Chave",
                        "content": "Resumo do plano de ação final: ângulo, canais, pergunta de abertura (string)."
                    }},
                    "custom_value_proposition_summary": {{
                        "title": "Proposta de Valor Principal (Customizada)",
                        "content": "A mensagem de valor mais impactante para este lead (string)."
                    }},
                    "potential_objections_summary": {{
                        "title": "Objeções Potenciais e Respostas Chave",
                        "content": "1-2 objeções mais prováveis e como lidar com elas (string)."
                    }},
                    "recommended_next_step": "A ação imediata que o vendedor deve tomar (string)."
                }}
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON.
            """

            formatted_prompt = prompt_template.format(
                all_lead_data_formatted_str=lead_data_for_prompt
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return InternalBriefingSummaryOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, InternalBriefingSummaryOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"InternalBriefingSummaryAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
            
            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return InternalBriefingSummaryOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "BRIEFING INTERNO DO LEAD:" in prompt:
                # Check if some key data points are in the prompt (simulating _format_dict_for_prompt)
                assert "Empresa Exemplo" in prompt 
                assert "Carlos Mendes" in prompt
                assert "Eficiência Consultiva" in prompt # From a potential action plan

                return (
                    "BRIEFING INTERNO DO LEAD:\n\n"
                    "**1. Visão Geral do Lead:**\n"
                    "   - **Empresa:** Empresa Exemplo (http://www.empresaexemplo.com)\n"
                    "   - **Descrição:** Atua no setor de TI, focada em otimizar processos, especialmente após recente expansão para LATAM.\n"
                    "   - **Oferta Nossa:** Nossas Soluções Incríveis de IA.\n\n"
                    "**2. Persona Principal Identificada:**\n"
                    "   - **Nome/Cargo:** Carlos Mendes, Diretor de Operações.\n"
                    "   - **Responsabilidades/Motivações:** Eficiência operacional, ROI claro, integração fácil de novas tecnologias, preocupado com complexidade e sobrecarga da equipe durante a expansão.\n\n"
                    "**3. Principais Dores e Necessidades:**\n"
                    "   - Processos manuais que não escalam com a expansão.\n"
                    "   - Necessidade de modernizar a pilha tecnológica sem interromper as operações.\n"
                    "   - Preocupação com custos e tempo de implementação de novas ferramentas.\n"
                    "   - **Conexão:** Nossas Soluções Incríveis de IA endereçam isso ao automatizar processos, oferecer integração ágil e ROI demonstrável.\n\n"
                    "**4. Gatilhos de Compra e Oportunidades:**\n"
                    "   - Anúncio de expansão para LATAM (aumenta a necessidade de eficiência).\n"
                    "   - Nomeação recente de Carlos Mendes como COO (novos líderes costumam revisar sistemas).\n"
                    "   - Menção explícita à busca por 'modernizar pilha de tecnologia'.\n\n"
                    "**5. Qualificação do Lead:**\n"
                    "   - **Avaliação:** Alto Potencial.\n"
                    "   - **Justificativa:** Dores claras, gatilhos presentes, persona com poder de decisão e alinhada com os benefícios da nossa solução, especialmente no contexto da expansão.\n\n"
                    "**6. Estratégia de Abordagem Chave:**\n"
                    "   - **Plano:** 'Eficiência Consultiva com Foco no Impacto da Expansão'.\n"
                    "   - **Ângulo:** Ajudar Carlos a mitigar desafios de eficiência na expansão com IA.\n"
                    "   - **Canais:** Email personalizado inicial -> Conexão LinkedIn -> Follow-up LinkedIn.\n"
                    "   - **Pergunta de Abertura (Email):** 'Carlos, com a expansão da Empresa Exemplo, como vocês estão priorizando a otimização de processos internos para sustentar esse crescimento?'\n\n"
                    "**7. Proposta de Valor Principal (Customizada):**\n"
                    "   - 'Carlos, vamos transformar os desafios da expansão da Empresa Exemplo em uma vantagem competitiva com operações mais inteligentes, usando IA para escalar eficientemente sem sobrecarregar sua equipe.'\n\n"
                    "**8. Possíveis Objeções e Respostas Chave:**\n"
                    "   - **Objeção:** 'Não temos orçamento / tempo agora devido à expansão.'\n"
                    "     **Resposta:** Posicionar a IA como um facilitador que otimiza custos e libera tempo justamente nesse cenário crítico.\n"
                    "   - **Objeção:** 'Parece complexo de implementar.'\n"
                    "     **Resposta:** Destacar a facilidade de integração e o suporte dedicado, mencionando que foi projetado para cenários como o da Empresa Exemplo.\n\n"
                    "**9. Próximo Passo Recomendado:**\n"
                    "   - Executar o Passo 1 do Plano de Abordagem Detalhado: Enviar o email personalizado para Carlos Mendes com o estudo de caso/infográfico."
                )
            return "Resposta padrão do mock."

    print("Running mock test for InternalBriefingSummaryAgent...")
    mock_llm = MockLLMClient()
    agent = InternalBriefingSummaryAgent(
        name="InternalBriefingSummaryAgent",
        description="Summarizes all lead data into an internal briefing.",
        llm_client=mock_llm
    )

    # Simulate the structure of all_lead_data based on what the prompt expects to summarize
    test_all_lead_data = {
        "nome_empresa": "Empresa Exemplo",
        "url_lead": "http://www.empresaexemplo.com",
        "produto_servico_sendo_oferecido": "Nossas Soluções Incríveis de IA",
        "analise_lead": "Empresa de TI, médio porte, expandindo para LATAM. Busca otimizar processos.",
        "persona_desenvolvida": "Carlos Mendes, Diretor de Operações. Foco: eficiência, ROI, integração fácil. Dores: processos manuais, complexidade.",
        "pontos_de_dor_aprofundados": "Dor principal: escalar operações eficientemente durante expansão. Preocupação com sobrecarga da equipe.",
        "gatilhos_de_compra": "Expansão LATAM, novo COO (Carlos Mendes), busca por modernização tecnológica.",
        "qualificacao_lead": "Alto Potencial: Dores claras, gatilhos, persona decisora.",
        "plano_de_acao_final": "Nome: 'Eficiência Consultiva com Foco no Impacto da Expansão'. Abordagem: Email -> LinkedIn. Pergunta: 'Como priorizam otimização na expansão?'",
        "propostas_de_valor_customizadas": "PV1: Escale expansão com IA. PV2: Modernize com ROI e fácil integração.",
        "respostas_objecoes": "Objeção Orçamento/Tempo: IA otimiza custos/tempo. Objeção Complexidade: Fácil integração e suporte.",
        "contatos_extraidos": {"emails_found": ["carlos.mendes@empresaexemplo.com"], "instagram_profiles_found": []}
        # Add other fields as gathered throughout a real process
    }

    input_data = InternalBriefingSummaryInput(all_lead_data=test_all_lead_data)
    output = agent.process(input_data)

    print(f"Briefing Summary Text: \n{output.briefing_summary_text}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "BRIEFING INTERNO DO LEAD:" in output.briefing_summary_text
    assert "Empresa Exemplo" in output.briefing_summary_text
    assert "Carlos Mendes" in output.briefing_summary_text
    assert "Nossas Soluções Incríveis de IA" in output.briefing_summary_text
    assert "Alto Potencial" in output.briefing_summary_text
    assert "Eficiência Consultiva" in output.briefing_summary_text # From action plan
    assert output.error_message is None
    print("Mock test completed.")
