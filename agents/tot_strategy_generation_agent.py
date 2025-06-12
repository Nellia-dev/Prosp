from typing import Optional, List
from pydantic import BaseModel, Field

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class ToTStrategyGenerationInput(BaseModel):
    current_lead_summary: str # This would be a summary of analysis, persona, pain points etc.
    product_service_offered: str

class ToTStrategyOptionModel(BaseModel):
    strategy_name: str
    angle_or_hook: str
    tone_of_voice: str
    primary_channels: List[str] # Changed from single channel to list
    key_points_or_arguments: List[str]
    opening_question: str

class ToTStrategyGenerationOutput(BaseModel):
    proposed_strategies: List[ToTStrategyOptionModel] = Field(default_factory=list)
    error_message: Optional[str] = None

class ToTStrategyGenerationAgent(BaseAgent[ToTStrategyGenerationInput, ToTStrategyGenerationOutput]):
    def __init__(self, llm_client: LLMClientBase):
        super().__init__(
            name="ToT Strategy Generation Agent",
            description="Generates multiple distinct approach strategies using a Tree of Thoughts-like framework.",
            llm_client=llm_client
        )
        # self.name = "ToTStrategyGenerationAgent" # Redundant

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: ToTStrategyGenerationInput) -> ToTStrategyGenerationOutput:
        proposed_strategies_text = ""
        error_message = None

        try:
            truncated_summary = self._truncate_text(input_data.current_lead_summary, GEMINI_TEXT_INPUT_TRUNCATE_CHARS - 500) # Reserve space for prompt

            prompt_template = """
                Você é um Gerador de Estratégias de Abordagem B2B, utilizando um framework similar ao "Tree of Thoughts" (ToT) para explorar múltiplas opções.
                Seu objetivo é propor 2-3 estratégias de abordagem distintas e criativas para o lead, com base no resumo fornecido e no produto/serviço oferecido.

                RESUMO ATUAL DO LEAD:
                {current_lead_summary}

                PRODUTO/SERVIÇO OFERECIDO:
                {product_service_offered}

                INSTRUÇÕES:
                Proponha de 2 a 3 estratégias de abordagem distintas e criativas. Para cada estratégia:
                1.  **strategy_name**: Dê um nome ou título breve para a estratégia.
                2.  **angle_or_hook**: Descreva o principal ângulo ou "gancho" da abordagem.
                3.  **tone_of_voice**: Sugira o tom de voz principal (ex: consultivo, direto, provocativo, de parceria).
                4.  **primary_channels**: Indique os principais canais de comunicação (como uma lista de strings, ex: ["Email", "LinkedIn", "Evento"]).
                5.  **key_points_or_arguments**: Liste de 2 a 3 pontos chave ou argumentos a serem destacados (como uma lista de strings).
                6.  **opening_question**: Formule uma pergunta de abertura impactante para iniciar a conversa.

                Pense "fora da caixa" e explore diferentes caminhos.
                Responda APENAS com um objeto JSON com a seguinte estrutura:
                {{
                    "proposed_strategies": [
                        {{
                            "strategy_name": "Nome da Estratégia 1",
                            "angle_or_hook": "Gancho da Estratégia 1",
                            "tone_of_voice": "Tom de Voz da Estratégia 1",
                            "primary_channels": ["Canal A", "Canal B"],
                            "key_points_or_arguments": ["Ponto Chave 1.1", "Ponto Chave 1.2"],
                            "opening_question": "Pergunta de Abertura da Estratégia 1"
                        }},
                        {{
                            "strategy_name": "Nome da Estratégia 2",
                            "angle_or_hook": "Gancho da Estratégia 2",
                            "tone_of_voice": "Tom de Voz da Estratégia 2",
                            "primary_channels": ["Canal C"],
                            "key_points_or_arguments": ["Ponto Chave 2.1", "Ponto Chave 2.2"],
                            "opening_question": "Pergunta de Abertura da Estratégia 2"
                        }}
                        // ... mais estratégias se aplicável
                    ]
                }}
                Não inclua nenhuma explicação ou texto adicional fora do objeto JSON.
            """

            formatted_prompt = prompt_template.format(
                current_lead_summary=truncated_summary,
                product_service_offered=input_data.product_service_offered
            )

            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                return ToTStrategyGenerationOutput(error_message="LLM call returned no response.")

            parsed_output = self.parse_llm_json_response(llm_response_str, ToTStrategyGenerationOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"ToTStrategyGenerationAgent JSON parsing failed. Raw response: {llm_response_str[:500]}")
            
            return parsed_output
        
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name}: {e}")
            import traceback
            traceback.print_exc()
            return ToTStrategyGenerationOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "ESTRATÉGIAS DE ABORDAGEM PROPOSTAS:" in prompt:
                return (
                    "ESTRATÉGIAS DE ABORDAGEM PROPOSTAS:\n\n"
                    "**Estratégia 1: O Desafio da Eficiência Oculta**\n"
                    "- Ângulo: Focar nos custos não óbvios e na perda de produtividade devido a processos ineficientes que o lead pode não ter quantificado.\n"
                    "- Tom de Voz: Consultivo e Analítico.\n"
                    "- Canais: Email inicial com link para um estudo de caso breve, seguido de contato no LinkedIn.\n"
                    "- Pontos Chave:\n"
                    "  1. Custo de oportunidade de manter processos X.\n"
                    "  2. Impacto da {product_service_offered} na redução de Y horas/semana.\n"
                    "  3. Benchmarks de eficiência no setor Z.\n"
                    "- Pergunta de Abertura: 'Muitas empresas no setor [setor do lead] não percebem o quanto processos legados podem estar custando em termos de [métrica chave]. Vocês já fizeram um levantamento interno sobre isso na Empresa Exemplo?'\n\n"
                    "**Estratégia 2: Parceria para Inovação Contínua**\n"
                    "- Ângulo: Posicionar o {product_service_offered} não como uma ferramenta, mas como um motor de inovação e adaptação futura.\n"
                    "- Tom de Voz: Visionário e de Parceria.\n"
                    "- Canais: Convite para um webinar exclusivo sobre tendências futuras, contato via LinkedIn com insights sobre inovação no setor do lead.\n"
                    "- Pontos Chave:\n"
                    "  1. Como {product_service_offered} facilita a adaptação a mudanças de mercado.\n"
                    "  2. Cases de co-criação de soluções com clientes.\n"
                    "  3. Visão de futuro para {product_service_offered} e o setor.\n"
                    "- Pergunta de Abertura: 'Carlos, considerando a velocidade das mudanças no setor de TI, como a Empresa Exemplo está se preparando para incorporar inovações tecnológicas de forma ágil nos próximos 2-3 anos?'"
                )
            return "Resposta padrão do mock."

    print("Running mock test for ToTStrategyGenerationAgent...")
    mock_llm = MockLLMClient()
    agent = ToTStrategyGenerationAgent(llm_client=mock_llm)

    test_lead_summary = (
        "Lead: Empresa Exemplo (Médio porte, TI). Persona: Carlos Mendes (Diretor de Operações), focado em eficiência, ROI e integração fácil. "
        "Principais dores: Otimização de processos manuais, integração de novas tecnologias. "
        "Gatilhos: Anúncio de expansão, busca por modernização."
    )
    test_product_service = "Nossas Soluções Incríveis de IA"

    input_data = ToTStrategyGenerationInput(
        current_lead_summary=test_lead_summary,
        product_service_offered=test_product_service
    )

    output = agent.process(input_data)

    print(f"Proposed Strategies Text: \n{output.proposed_strategies_text}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "Estratégia 1:" in output.proposed_strategies_text
    assert "Estratégia 2:" in output.proposed_strategies_text
    assert "Nossas Soluções Incríveis de IA" in output.proposed_strategies_text
    assert output.error_message is None
    print("Mock test completed.")
