from typing import Optional
from pydantic import BaseModel

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000 # Assuming this is a reasonable limit for the combined context

class B2BPersonaCreationInput(BaseModel):
    lead_analysis: str
    product_service_offered: str
    lead_url: str

class B2BPersonaCreationOutput(BaseModel):
    persona_profile: str
    error_message: Optional[str] = None

class B2BPersonaCreationAgent(BaseAgent[B2BPersonaCreationInput, B2BPersonaCreationOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase):
        super().__init__(name=name, description=description, llm_client=llm_client)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: B2BPersonaCreationInput) -> B2BPersonaCreationOutput:
        persona_profile = ""
        error_message = None

        try:
            # Consider the total length of content being inserted into the prompt
            # For simplicity, truncating lead_analysis primarily.
            # A more sophisticated approach might budget characters for each section.
            truncated_analysis = self._truncate_text(input_data.lead_analysis, GEMINI_TEXT_INPUT_TRUNCATE_CHARS - 2000) # Reserve ~2k for rest of prompt
            
            # Refined prompt_template
            prompt_template = """
                Você é um Especialista em Marketing B2B e Criação de Personas, com foco no mercado brasileiro. Sua tarefa é criar um perfil de persona detalhado e narrativo para um tomador de decisão chave, com base na análise do lead, no produto/serviço que sua empresa oferece, e na URL do lead.

                ANÁLISE DO LEAD (fornecida pela nossa equipe de inteligência):
                \"\"\"
                {lead_analysis}
                \"\"\"

                NOSSO PRODUTO/SERVIÇO (que queremos apresentar a esta persona):
                "{product_service_offered}"

                URL DO LEAD (para sua referência e contexto adicional, se necessário):
                {lead_url}

                INSTRUÇÕES PARA CRIAÇÃO DO PERFIL DA PERSONA:
                Desenvolva um perfil narrativo coeso e detalhado que traga vida a este tomador de decisão. O perfil deve ser escrito em português do Brasil e especificamente adaptado ao contexto empresarial brasileiro.

                O perfil deve cobrir, de forma integrada e fluida, os seguintes aspectos:
                1.  **Nome Fictício Brasileiro e Cargo Provável:** Atribua um nome comum no Brasil e o cargo mais provável para este tomador de decisão, com base na análise do lead.
                2.  **Principais Responsabilidades e Desafios Diários:** Descreva suas funções chave e os obstáculos que enfrenta regularmente.
                3.  **Objetivos Profissionais e Motivações:** O que ele(a) busca alcançar na carreira e o que o(a) impulsiona.
                4.  **Comportamento de Busca e Decisão B2B:** Como essa persona tipicamente busca soluções para seus desafios de negócios e quais fatores influenciam suas decisões de compra.
                5.  **Estilo de Comunicação e Canais Preferidos:** Como prefere ser abordado(a) e quais canais de comunicação profissional mais utiliza (ex: LinkedIn, email formal, WhatsApp para contatos próximos).
                6.  **Proposta de Valor Específica:** Como o NOSSO PRODUTO/SERVIÇO ("{product_service_offered}") pode especificamente ajudar essa persona a superar seus desafios e atingir seus objetivos. Seja claro e direto nesta parte.

                ESTILO E FORMATO DA SAÍDA:
                - O perfil deve ser um **texto corrido (narrativa)**, descritivo e envolvente.
                - **Não use formato JSON** ou qualquer outra estrutura de dados formal.
                - Mantenha o texto conciso, idealmente com um máximo de **350 palavras**, garantindo que todos os 6 pontos acima sejam cobertos.
                - O tom deve ser profissional, mas perspicaz, fornecendo insights úteis para uma equipe de vendas.

                Comece diretamente com o perfil.

                PERFIL DA PERSONA:
            """

            formatted_prompt = prompt_template.format(
                lead_analysis=truncated_analysis,
                product_service_offered=input_data.product_service_offered,
                lead_url=input_data.lead_url
            )

            llm_response = self.generate_llm_response(formatted_prompt)

            if llm_response:
                persona_profile = llm_response.strip() # Added strip()
            else:
                error_message = "LLM call returned no response or an empty response."
                self.logger.warning(f"{self.name} received an empty response from LLM for URL: {input_data.lead_url}")
        
        except Exception as e:
            import traceback
            self.logger.error(f"An unexpected error occurred in {self.name} for URL {input_data.lead_url}: {str(e)}\n{traceback.format_exc()}")
            error_message = f"An unexpected error occurred in {self.name}: {str(e)}"

        return B2BPersonaCreationOutput(
            persona_profile=persona_profile,
            error_message=error_message
        )

if __name__ == '__main__':
    # Ensure logger is available for __main__ block or use print
    from loguru import logger
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt:\n{prompt[:500]}...") # Log snippet of prompt
            if "PERFIL DA PERSONA:" in prompt:
                return (
                    "  Carlos Mendes, Diretor de Operações da Empresa ExemploTech, sediada em Campinas, SP, enfrenta o desafio constante de otimizar processos e reduzir custos operacionais em um mercado tecnológico competitivo. "
                    "Suas responsabilidades incluem garantir a eficiência da produção de software e a rápida implementação de novas tecnologias para manter a empresa à frente. "
                    "Carlos busca soluções que demonstrem um ROI claro e sejam fáceis de integrar com os sistemas legados, minimizando a disrupção. Ele é motivado por reconhecimento profissional e por entregar resultados mensuráveis que impactem positivamente o bottom-line. "
                    "Para se manter atualizado, Carlos participa de webinars técnicos e lê artigos em portais especializados do setor de TI. Ele valoriza a comunicação direta, baseada em dados, e prefere e-mails formais ou apresentações concisas no LinkedIn para o primeiro contato. "
                    "Nossas Soluções Incríveis de automação inteligente podem ajudá-lo a automatizar tarefas manuais de desenvolvimento e QA, fornecendo dados em tempo real para decisões mais assertivas e rápidas, alinhando-se com seu objetivo de modernização e eficiência. Isso liberaria sua equipe para focar em inovação, um ponto crucial para a ExemploTech. "
                ).strip() # Ensure no leading/trailing spaces from mock
            return "Resposta padrão do mock."

    logger.info("Running mock test for B2BPersonaCreationAgent...")
    mock_llm = MockLLMClient()
    # Providing name and description as per BaseAgent's __init__
    agent = B2BPersonaCreationAgent(name="TestB2BPersonaAgent", description="Test Agent", llm_client=mock_llm)

    test_lead_analysis = (
        "A Empresa ExemploTech, localizada em Campinas, São Paulo, atua no setor de Tecnologia da Informação, oferecendo principalmente soluções de software como serviço (SaaS) para gestão de projetos. "
        "Trata-se de uma empresa de médio porte, com cerca de 150 funcionários, e que recentemente anunciou uma rodada de investimento para expandir suas operações na América Latina. "
        "Seus principais desafios divulgados incluem a necessidade de escalar suas operações de desenvolvimento de software de forma eficiente e otimizar processos internos para suportar o crescimento acelerado. "
        "Buscam inovação constante para se manterem competitivos."
    )
    test_product_service = "Nossas Soluções Incríveis de automação inteligente para DEVs e QA"
    test_lead_url = "http://www.empresaexemplotec.com.br"

    input_data = B2BPersonaCreationInput(
        lead_analysis=test_lead_analysis,
        product_service_offered=test_product_service,
        lead_url=test_lead_url
    )

    output = agent.process(input_data)

    logger.info(f"Persona Profile:\n{output.persona_profile}")
    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("Persona profile generated successfully.")

    assert "Carlos Mendes" in output.persona_profile
    assert "Nossas Soluções Incríveis" in output.persona_profile
    assert "Campinas" in output.persona_profile # Check if context was used
    assert output.error_message is None
    logger.info("Mock test completed successfully.")
```
