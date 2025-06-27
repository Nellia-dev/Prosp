import asyncio
import json
import time
import traceback
from textwrap import dedent
from typing import List

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
        **kwargs
    ):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)

    async def process(self, lead_id: str, job_id: str, input_data: PainPointDeepeningInput) -> PainPointDeepeningOutput:
        """
        Deepens the analysis of pain points for a given persona.
        """
        start_time = time.time()
        await self._emit_event("agent_start", {
            "agent_name": self.name,
            "job_id": job_id,
            "lead_id": lead_id,
            "agent_description": self.description,
            "input_data": input_data.model_dump()
        })
        logger.info(f"🕵️ Deepening pain points for {input_data.company_name} (Lead: {lead_id})")

        if not input_data.personas:
            logger.warning(f"No personas provided for Lead {lead_id}. Skipping pain point deepening.")
            output = PainPointDeepeningOutput(pain_points=[])
            duration = time.time() - start_time
            await self._emit_event("agent_end", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "duration": duration,
                "output": output.model_dump()
            })
            return output

        try:
            # For simplicity, we focus on the first persona
            persona = input_data.personas[0]

            prompt = dedent(f"""
                You are a solution-oriented sales engineer with deep empathy for customer challenges. Your task is to analyze a buyer persona and our product description to identify and elaborate on their most critical pain points.

                For the given persona, identify 3-5 key pain points. For each one, describe its business implication and how our product offers a direct solution.

                Our Product/Service Description:
                ---
                {input_data.product_service_description}
                ---

                Target Buyer Persona:
                - Name: {persona.name}
                - Title: {persona.title}
                - Description: {persona.description}
                ---

                RESPONSE FORMAT:
                Respond EXCLUSIVELY with a valid JSON array of objects. Each object must have the keys "pain_point", "implication", and "solution_fit".
                Do NOT include ANY text, explanation, or markdown (like ```json) before or after the JSON object.
                Example:
                [
                    {{
                        "pain_point": "Specific challenge the persona faces.",
                        "implication": "Negative business impact of the challenge.",
                        "solution_fit": "How our product resolves this specific challenge."
                    }}
                ]
            """)

            logger.debug(f"Prompt for {self.name} (Lead: {lead_id}):\n{prompt[:500]}...")
            
            llm_response = await asyncio.to_thread(self.llm_client.generate, prompt)

            if not llm_response or not llm_response.content:
                raise ValueError("LLM call returned no response or empty content.")

            response_text = llm_response.content
            if response_text.strip().startswith("```json"):
                response_text = response_text.strip()[7:-3].strip()

            pain_points_data = json.loads(response_text)
            pain_points = [PainPoint(**p) for p in pain_points_data]
            
            output = PainPointDeepeningOutput(pain_points=pain_points)
            
            logger.info(f"✅ Successfully identified {len(output.pain_points)} pain points for Lead {lead_id}.")

            duration = time.time() - start_time
            await self._emit_event("agent_end", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "duration": duration,
                "output": output.model_dump()
            })
            return output

        except Exception as e:
            duration = time.time() - start_time
            error_message = f"An unexpected error occurred in {self.name}: {e}"
            logger.error(error_message, exc_info=True)
            await self._emit_event("pipeline_error", {
                "agent_name": self.name,
                "job_id": job_id,
                "lead_id": lead_id,
                "duration": duration,
                "error_message": str(e),
                "details": traceback.format_exc()
            })
            raise

if __name__ == '__main__':
    import sys
    from core_logic.llm_client import MockLLMResponse

    logger.remove()
    logger.add(sys.stderr, level="INFO")

    class MockLLMClient(LLMClientBase):
        def generate(self, prompt: str, **kwargs) -> MockLLMResponse:
            logger.info("MockLLMClient generating response...")
            mock_json_response = json.dumps([
                {
                    "pain_point": "Manual QA processes are slow and error-prone.",
                    "implication": "Delayed product releases and potential for critical bugs reaching customers.",
                    "solution_fit": "Our AI-powered automation platform can run QA cycles 10x faster and detect more bugs."
                },
                {
                    "pain_point": "Difficulty integrating new tech with legacy systems.",
                    "implication": "High integration costs and long time-to-value for new tools.",
                    "solution_fit": "Our platform includes robust APIs and pre-built connectors to simplify integration."
                }
            ])
            return MockLLMResponse(content=mock_json_response)

    async def main():
        mock_llm = MockLLMClient()
        event_queue = asyncio.Queue()
        agent = PainPointDeepeningAgent(
            llm_client=mock_llm,
            event_queue=event_queue,
            user_id="test_user"
        )

        test_input = PainPointDeepeningInput(
            company_name="Innovate Corp",
            product_service_description="AI-powered QA automation platform.",
            personas=[
                Persona(
                    name="Jane Doe",
                    title="Director of Engineering",
                    description="Responsible for product delivery speed and quality. Worried about scaling the team and processes."
                )
            ]
        )

        lead_id = "lead_pain_123"
        job_id = "job_pain_456"

        logger.info(f"--- Running Test for {agent.name} ---")
        output = await agent.process(lead_id, job_id, test_input)

        logger.info(f"\n--- Agent Output ---")
        logger.info(json.dumps(output.model_dump(), indent=2))
        assert len(output.pain_points) == 2
        assert output.pain_points[0].pain_point == "Manual QA processes are slow and error-prone."

        logger.info("\n--- Verifying Emitted Events ---")
        event_count = 0
        while not event_queue.empty():
            event = await event_queue.get()
            logger.info(f"Event received: {event['event_type']} for lead {event['payload']['lead_id']}")
            event_count += 1
        assert event_count == 2

        logger.info(f"\n✅ Test for {agent.name} completed successfully.")

    asyncio.run(main())
