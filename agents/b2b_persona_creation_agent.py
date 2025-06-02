from typing import Optional
from pydantic import BaseModel

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class B2BPersonaCreationInput(BaseModel):
    lead_analysis: str
    product_service_offered: str
    lead_url: str  # Added lead_url as per subtask, can be used in prompt

class B2BPersonaCreationOutput(BaseModel):
    persona_profile: str
    error_message: Optional[str] = None

class B2BPersonaCreationAgent(BaseAgent[B2BPersonaCreationInput, B2BPersonaCreationOutput]):
    def __init__(self, llm_client: LLMClientBase):
        super().__init__(llm_client)
        self.name = "B2BPersonaCreationAgent"

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: B2BPersonaCreationInput) -> B2BPersonaCreationOutput:
        persona_profile = ""
        error_message = None

        try:
            truncated_analysis = self._truncate_text(input_data.lead_analysis, GEMINI_TEXT_INPUT_TRUNCATE_CHARS // 2)
            
            prompt_template = """
                Você é um Especialista em Marketing B2B e Vendas. Sua tarefa é criar um perfil de persona detalhado para um tomador de decisão chave, com base na análise do lead e no produto/serviço oferecido. Considere o contexto do mercado brasileiro.

                ANÁLISE DO LEAD:
                {lead_analysis}

                PRODUTO/SERVIÇO OFERECIDO PELA SUA EMPRESA:
                {product_service_offered}

                URL DO LEAD (para referência contextual, se necessário):
                {lead_url}

                INSTRUÇÕES:
                Crie um perfil de persona que inclua:
                1.  Nome fictício brasileiro e cargo provável do tomador de decisão.
                2.  Principais responsabilidades e desafios diários.
                3.  Objetivos profissionais e motivações.
                4.  Como a persona busca soluções e toma decisões de compra B2B.
                5.  Estilo de comunicação preferido e canais que utiliza.
                6.  Como o {product_service_offered} pode ajudar essa persona a superar seus desafios e atingir seus objetivos.

                O perfil deve ser um texto corrido, descritivo e envolvente. Não use formato JSON.
                Máximo de 350 palavras.

                PERFIL DA PERSONA:
            """

            formatted_prompt = prompt_template.format(
                lead_analysis=truncated_analysis,
                product_service_offered=input_data.product_service_offered,
                lead_url=input_data.lead_url
            )

            llm_response = self.generate_llm_response(formatted_prompt)

            if llm_response:
                persona_profile = llm_response
            else:
                error_message = "LLM call returned no response or an empty response."
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_message = f"An unexpected error occurred in {self.name}: {str(e)}"

        return B2BPersonaCreationOutput(
            persona_profile=persona_profile,
            error_message=error_message
        )

if __name__ == '__main__':
    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            if "PERFIL DA PERSONA:" in prompt:
                return (
                    "Carlos Mendes, Diretor de Operações da Empresa Exemplo, enfrenta o desafio constante de otimizar processos e reduzir custos. "
                    "Suas responsabilidades incluem garantir a eficiência da produção e a implementação de novas tecnologias. "
                    "Carlos busca soluções que demonstrem ROI claro e sejam fáceis de integrar. Ele valoriza a comunicação direta e se mantém informado através de webinars e artigos do setor. "
                    "Nossas Soluções Incríveis podem ajudá-lo a automatizar tarefas manuais, fornecendo dados em tempo real para decisões mais assertivas, alinhando-se com seu objetivo de modernização."
                )
            return "Resposta padrão do mock."

    print("Running mock test for B2BPersonaCreationAgent...")
    mock_llm = MockLLMClient()
    agent = B2BPersonaCreationAgent(llm_client=mock_llm)

    test_lead_analysis = (
        "A Empresa Exemplo atua no setor de Tecnologia da Informação, oferecendo principalmente soluções de software como serviço (SaaS). "
        "Parece ser uma empresa de médio porte. Seus principais desafios podem incluir a necessidade de otimizar processos internos."
    )
    test_product_service = "Nossas Soluções Incríveis"
    test_lead_url = "http://www.empresaexemplo.com"

    input_data = B2BPersonaCreationInput(
        lead_analysis=test_lead_analysis,
        product_service_offered=test_product_service,
        lead_url=test_lead_url
    )

    output = agent.process(input_data)

    print(f"Persona Profile: {output.persona_profile}")
    if output.error_message:
        print(f"Error: {output.error_message}")

    assert "Carlos Mendes" in output.persona_profile
    assert "Nossas Soluções Incríveis" in output.persona_profile
    assert output.error_message is None
    print("Mock test completed.")
