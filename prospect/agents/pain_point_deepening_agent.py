import asyncio
import json
import textwrap
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel, Field

from .base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Data Models
class Persona(BaseModel):
    name: str
    title: str
    description: str

class PainPoint(BaseModel):
    pain_point: str = Field(description="A specific pain point the persona likely experiences.")
    implication: str = Field(description="The business implication of this pain point if not addressed.")
    solution_fit: str = Field(description="How our product/service directly addresses this pain point.")

class PainPointDeepeningInput(BaseModel):
    company_name: str
    product_service_description: str
    personas: List[Persona]

class PainPointDeepeningOutput(BaseModel):
    pain_points: List[PainPoint] = Field(default_factory=list)
    error_message: Optional[str] = Field(default=None)

# Agent Definition
class PainPointDeepeningAgent(BaseAgent[PainPointDeepeningInput, PainPointDeepeningOutput]):
    """
    Agent specialized in deepening the understanding of customer pain points.
    """

    def __init__(
        self,
        llm_client: LLMClientBase,
        name: str = "Pain Point Deepening Agent",
        description: str = "Deepens the understanding of customer pain points based on persona and initial analysis.",
        event_queue: Optional[asyncio.Queue] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(llm_client, name, description, event_queue, user_id)

    async def process(self, lead_id: str, input_data: PainPointDeepeningInput) -> PainPointDeepeningOutput:
        """
        Deepens the analysis of pain points for a given persona.
        """
        await self._emit_event("agent_start", {"agent_name": self.name, "lead_id": lead_id})
        logger.info(f"Starting Pain Point Deepening for {input_data.company_name} (Lead ID: {lead_id})")

        if not input_data.personas:
            logger.warning(f"No personas found for Lead ID {lead_id}. Skipping pain point deepening.")
            output = PainPointDeepeningOutput(
                pain_points=[],
                error_message="No personas provided.",
            )
            await self._emit_event("agent_end", {"agent_name": self.name, "lead_id": lead_id, "response": output.model_dump()})
            return output

        persona = input_data.personas[0]

        system_prompt = textwrap.dedent(
            """
            You are a solution-oriented sales engineer with deep empathy for customer challenges. Your task is to analyze a buyer persona and our product description to identify and elaborate on their most critical pain points.

            For the given persona, identify 3-5 key pain points. For each one, describe its business implication and how our product offers a direct solution.

            Output the result as a JSON array of objects. Each object must have the keys "pain_point", "implication", and "solution_fit".
            Do not include any other text or explanations outside of the JSON array.
            """
        )

        user_prompt = textwrap.dedent(
            f"""
            Our Product/Service Description:
            {input_data.product_service_description}

            Target Buyer Persona:
            - Name: {persona.name}
            - Title: {persona.title}
            - Description: {persona.description}

            Based on this, generate the detailed pain point analysis in the specified JSON format.
            """
        )

        response_text = await self.llm_client.generate(system_prompt, user_prompt)

        pain_points = []
        error_message = None
        try:
            # Handle markdown code blocks
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()

            pain_points_data = json.loads(response_text)
            pain_points = [PainPoint(**p) for p in pain_points_data]
            logger.info(f"Successfully parsed {len(pain_points)} pain points for Lead ID {lead_id}.")
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            error_message = f"Failed to parse Pain Points from LLM response: {e}"
            logger.error(f"{error_message} for Lead ID {lead_id}")
            logger.debug(f"LLM Response Text: {response_text}")

        output = PainPointDeepeningOutput(pain_points=pain_points, error_message=error_message)

        logger.info(f"Finished Pain Point Deepening for {input_data.company_name} (Lead ID: {lead_id})")
        await self._emit_event("agent_end", {"agent_name": self.name, "lead_id": lead_id, "response": output.model_dump()})

        return output

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
                "primary_pain_category": "Eficiência Operacional e Escalabilidade",
                "detailed_pain_points": [
                    {
                        "pain_point_title": "Otimização de Processos Manuais em Expansão",
                        "detailed_description": "A Empresa Exemplo, ao expandir para LATAM, enfrenta desafios com processos manuais que não escalam, especialmente em QA, gerando lentidão e potenciais erros.",
                        "potential_business_impact": "Atrasos em lançamentos de produtos/features, aumento de custos operacionais para manter a qualidade, dificuldade em atender a nova demanda do mercado LATAM.",
                        "how_our_solution_helps": "Nossas Soluções Incríveis de Automação com IA podem automatizar ciclos de QA repetitivos e complexos, liberando a equipe para focar em testes mais estratégicos e acelerando o time-to-market.",
                        "investigative_questions": [
                            "Como a expansão para LATAM está impactando especificamente os prazos de entrega de software?",
                            "Quais são os principais gargalos que vocês percebem nos processos de QA atualmente?"
                        ]
                    },
                    {
                        "pain_point_title": "Integração de Novas Tecnologias com Sistemas Legados",
                        "detailed_description": "A busca por modernização tecnológica mencionada pela Empresa Exemplo pode ser dificultada pela necessidade de integrar novas ferramentas com sistemas já existentes, um desafio comum para Diretores de Operações como Carlos Mendes.",
                        "potential_business_impact": "Aumento da complexidade técnica, custos de integração elevados, possível resistência da equipe a múltiplas ferramentas desconexas, tempo maior para obter valor das novas tecnologias.",
                        "how_our_solution_helps": "Nossas Soluções Incríveis de Automação com IA são projetadas com foco em integração facilitada (APIs robustas, conectores) e oferecem um dashboard unificado, simplificando a gestão.",
                        "investigative_questions": [
                            "Carlos, ao considerar novas tecnologias, qual é sua maior preocupação em relação à integração com o stack tecnológico atual da Empresa Exemplo?",
                            "Como a equipe técnica costuma lidar com a curva de aprendizado e adoção de novas plataformas?"
                        ]
                    }
                ],
                "urgency_level": "high",
                "overall_pain_summary": "A Empresa Exemplo possui dores significativas relacionadas à eficiência e escalabilidade de seus processos de TI, especialmente QA, impulsionadas pela expansão. Há uma necessidade clara de modernização e automação."
            })

    logger.info("Running mock test for PainPointDeepeningAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = PainPointDeepeningAgent(
        name="TestPainPointDeepeningAgent",
        description="Test Agent for Pain Point Deepening",
        llm_client=mock_llm
    )

    test_lead_analysis = "A Empresa Exemplo (médio porte, setor de TI) enfrenta desafios na otimização de processos internos, muitos ainda manuais, para suportar sua recente expansão para o mercado LATAM. Ganhou prêmios de inovação e busca modernizar sua pilha de tecnologia."
    test_persona_profile = "Carlos Mendes é o Diretor de Operações da Empresa Exemplo. Suas principais responsabilidades incluem garantir a eficiência operacional e a implementação de novas tecnologias. Ele busca soluções com ROI claro e que sejam de fácil integração. É motivado por resultados mensuráveis e pelo reconhecimento de otimizar a operação da empresa. Seu estilo de comunicação é direto e formal."
    test_product_service = "Nossas Soluções Incríveis de Automação com IA para QA e DevOps"
    test_company_name = "Empresa Exemplo"

    input_data = PainPointDeepeningInput(
        lead_analysis=test_lead_analysis,
        persona_profile=test_persona_profile,
        product_service_offered=test_product_service,
        company_name=test_company_name
    )

    output = agent.process(input_data)

    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("PainPointDeepeningAgent processed successfully.")
        logger.info(f"Primary Pain Category: {output.primary_pain_category}")
        logger.info(f"Urgency Level: {output.urgency_level}")
        logger.info(f"Overall Pain Summary: {output.overall_pain_summary}")
        logger.info(f"Detailed Pain Points ({len(output.detailed_pain_points)}):")
        for i, dp_point in enumerate(output.detailed_pain_points):
            logger.info(f"  Pain Point {i+1}: {dp_point.pain_point_title}")
            logger.info(f"    Description: {dp_point.detailed_description}")
            logger.info(f"    Impact: {dp_point.potential_business_impact}")
            logger.info(f"    Solution Fit: {dp_point.how_our_solution_helps}")
            logger.info(f"    Investigative Questions: {dp_point.investigative_questions}")

    assert output.error_message is None
    assert output.primary_pain_category == "Eficiência Operacional e Escalabilidade"
    assert len(output.detailed_pain_points) == 2
    assert "expansão para LATAM" in output.detailed_pain_points[0].detailed_description
    assert len(output.detailed_pain_points[0].investigative_questions) > 0
    assert output.urgency_level == "high"
    assert output.overall_pain_summary is not None

    logger.info("\nMock test for PainPointDeepeningAgent completed successfully.")
