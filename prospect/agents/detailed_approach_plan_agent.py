from typing import Optional, List
from pydantic import BaseModel, Field, validator
import json # Ensure json is imported

from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

# Constants
GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000

class DetailedApproachPlanInput(BaseModel):
    lead_analysis: str # Summary of company, sector, challenges etc.
    persona_profile: str # Detailed description of the target persona
    deepened_pain_points: str # JSON string of PainPointAnalysisOutput (includes investigative questions)
    final_action_plan_text: str # JSON string of ToTActionPlanSynthesisOutput (Synthesized plan from ToT agents)
    product_service_offered: str # User's product/service
    lead_url: str # Lead's website URL

# Sub-models for structured output
class ContactStepDetail(BaseModel):
    step_number: int
    channel: str # E.g., "Email Personalizado", "LinkedIn (Nota de Conexão)", "Telefone"
    objective: str # Specific goal for this step
    key_topics_arguments: List[str] = Field(default_factory=list) # Main points to convey
    key_questions: List[str] = Field(default_factory=list) # Key questions to ask (if any)
    cta: str # Specific call to action for this step
    supporting_materials: Optional[str] = None # E.g., link to case study, article
    
    @validator('key_questions', 'key_topics_arguments', pre=True, always=True)
    def ensure_list_of_strings(cls, v_list, field):
        if v_list is None:
            return []
        if isinstance(v_list, str):
            # Split string by newline if it seems to be a multi-line string meant as a list
            # Otherwise, wrap the single string in a list.
            # This handles cases where LLM might provide a single string instead of a list of one.
            return [s.strip() for s in v_list.splitlines() if s.strip()] if '\n' in v_list else ([v_list.strip()] if v_list.strip() else [])
        if isinstance(v_list, list) and all(isinstance(item, str) for item in v_list):
            return [s.strip() for s in v_list if s.strip()] # Clean up strings in list
        # If it's a list but not all strings, or some other type, log/handle appropriately or return empty
        # For now, returning as is if it's a list, Pydantic will catch type errors for items.
        # Or, to be safer for this specific use case:
        if isinstance(v_list, list): # Filter out non-string elements or convert
            processed_list = []
            for item in v_list:
                if isinstance(item, str):
                    if item.strip(): processed_list.append(item.strip())
                # Optionally convert other types to string, or skip non-strings
                # else: processed_list.append(str(item))
            return processed_list
        return [] # Default to empty list if input is not easily convertible

class DetailedApproachPlanOutput(BaseModel):
    main_objective: str = "Objetivo principal da abordagem não especificado."
    adapted_elevator_pitch: str = "Elevator pitch adaptado não especificado."
    contact_sequence: List[ContactStepDetail] = Field(default_factory=list)
    engagement_indicators_to_monitor: List[str] = Field(default_factory=list)
    potential_obstacles_attention_points: List[str] = Field(default_factory=list)
    suggested_next_steps_if_successful: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

    @validator('contact_sequence', pre=True, always=True)
    def ensure_contact_sequence_is_list(cls, v):
        if v is None: return []
        return v if isinstance(v, list) else []

    @validator('engagement_indicators_to_monitor', 'potential_obstacles_attention_points', 'suggested_next_steps_if_successful', pre=True, always=True)
    def ensure_string_list_fields(cls, v_list, field):
        return ContactStepDetail.ensure_list_of_strings(v_list, field)


class DetailedApproachPlanAgent(BaseAgent[DetailedApproachPlanInput, DetailedApproachPlanOutput]):
    def __init__(self, name: str, description: str, llm_client: LLMClientBase, **kwargs):
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        # Logger is already initialized in BaseAgent as self.logger

    def _truncate_text(self, text: str, max_chars: int) -> str:
        """Truncates text to a maximum number of characters."""
        return text[:max_chars]

    def process(self, input_data: DetailedApproachPlanInput) -> DetailedApproachPlanOutput:
        error_message = None

        try:
            # Approximate character allocation, leaving room for prompt overhead (approx 2.5k for fixed parts)
            # Total GEMINI_TEXT_INPUT_TRUNCATE_CHARS = 180000
            base_prompt_overhead = 3000
            available_chars_for_inputs = GEMINI_TEXT_INPUT_TRUNCATE_CHARS - base_prompt_overhead

            # Distribute remaining characters among dynamic inputs
            # Prioritize final_action_plan_text and deepened_pain_points
            tr_final_action_plan = self._truncate_text(input_data.final_action_plan_text, int(available_chars_for_inputs * 0.35))
            tr_deepened_pain_points = self._truncate_text(input_data.deepened_pain_points, int(available_chars_for_inputs * 0.25))
            tr_lead_analysis = self._truncate_text(input_data.lead_analysis, int(available_chars_for_inputs * 0.20))
            tr_persona_profile = self._truncate_text(input_data.persona_profile, int(available_chars_for_inputs * 0.20))

            # Refined prompt
            prompt_template = """
                Você é um Estrategista de Contas Sênior e Coach de Vendas B2B, especializado em criar planos de engajamento multi-etapa acionáveis e eficazes, com foco no mercado brasileiro.
                Sua tarefa é expandir o "Plano de Ação Final Sintetizado" fornecido em um "Plano de Abordagem Detalhado" que uma equipe de vendas possa executar.

                PLANO DE AÇÃO FINAL SINTETIZADO (Estratégia de Alto Nível):
                \"\"\"
                {final_action_plan_text}
                \"\"\"

                INFORMAÇÕES DE CONTEXTO ADICIONAIS SOBRE O LEAD:
                - Análise do Lead: {lead_analysis}
                - Perfil da Persona Alvo: {persona_profile}
                - Pontos de Dor Aprofundados (incluindo perguntas investigativas): {deepened_pain_points}
                - Produto/Serviço que estamos oferecendo: {product_service_offered}
                - URL do Lead (para referência): {lead_url}

                INSTRUÇÕES PARA O PLANO DETALHADO:
                Com base no "Plano de Ação Final Sintetizado" e em TODAS as informações de contexto, detalhe os seguintes aspectos.
                O plano deve ser prático, com passos claros e adaptado às nuances de comunicação e negócios no Brasil.
                Crie uma sequência de contato inicial de 3 a 4 passos.

                FORMATO DA RESPOSTA:
                Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo. Não inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.

                SCHEMA JSON ESPERADO:
                {{
                    "main_objective": "string - Reafirme ou refine o objetivo principal e estratégico desta abordagem completa, derivado do Plano de Ação Final.",
                    "adapted_elevator_pitch": "string - Crie uma 'mensagem central' ou 'elevator pitch' de 2-3 frases, altamente personalizado para ESTE lead e persona, destacando o benefício mais crucial do '{product_service_offered}'.",
                    "contact_sequence": [ // Lista detalhando os primeiros 3-4 passos da sequência de contato.
                        {{
                            "step_number": "integer - O número do passo na sequência (1, 2, 3, ...).",
                            "channel": "string - Canal de contato para este passo (ex: 'Email Personalizado', 'LinkedIn (Nota de Conexão)', 'Telefone para Follow-up Breve', 'WhatsApp Mensagem Curta').",
                            "objective": "string - Objetivo específico e mensurável deste passo (ex: 'Obter resposta ao email inicial e validar interesse', 'Agendar uma chamada de descoberta de 15 minutos', 'Confirmar o principal desafio X da persona').",
                            "key_topics_arguments": ["string", ...], // Lista de 2-3 tópicos ou argumentos chave a serem abordados neste passo, alinhados com o elevator pitch e as dores da persona. Lista vazia [] se não houver tópicos específicos além da mensagem principal.
                            "key_questions": ["string", ...], // Lista opcional de 1-2 perguntas chave a serem feitas neste passo para engajar, qualificar ou descobrir informações. Lista vazia [] se não aplicável.
                            "cta": "string - Call to Action (Chamada para Ação) específica e clara para este passo (ex: 'Propor um horário para uma breve conversa de 15 min', 'Pedir para conectar no LinkedIn', 'Perguntar qual o melhor momento para um follow-up rápido').",
                            "supporting_materials": "string | null" // Opcional: Recurso/material de apoio a ser usado ou mencionado neste passo (ex: 'Link para estudo de caso sobre [problema similar]', 'Artigo do blog sobre [tópico de interesse da persona]', 'Vídeo curto de demonstração'). Use null se não houver.
                        }}
                    ],
                    "engagement_indicators_to_monitor": ["string", ...], // Lista de 2-3 indicadores chave para monitorar o engajamento do lead ao longo da sequência (ex: 'Taxa de abertura e cliques em emails', 'Aceitação de convite no LinkedIn', 'Respostas às mensagens diretas', 'Visitas ao site provenientes de links enviados'). Lista vazia [] se não houver indicadores específicos além de respostas diretas.
                    "potential_obstacles_attention_points": ["string", ...], // Lista de 2-3 potenciais obstáculos, desafios ou pontos de atenção que a equipe de vendas deve considerar ao executar este plano (ex: 'Lead pode estar extremamente ocupado devido a [evento recente]', 'Possível ceticismo inicial sobre [aspecto da solução]', 'Necessidade de contornar gatekeeper para primeiro contato'). Lista vazia [] se não houver pontos específicos.
                    "suggested_next_steps_if_successful": ["string", ...] // Lista de 1-2 próximos passos sugeridos caso a sequência inicial de contato seja bem-sucedida e o objetivo principal seja alcançado (ex: 'Agendar demonstração detalhada do produto', 'Preparar proposta personalizada com base na chamada de descoberta', 'Introduzir especialista técnico da nossa equipe'). Lista vazia [] se o plano já cobre isso."
                }}
            """

            formatted_prompt = prompt_template.format(
                final_action_plan_text=tr_final_action_plan,
                lead_analysis=tr_lead_analysis,
                persona_profile=tr_persona_profile,
                deepened_pain_points=tr_deepened_pain_points,
                product_service_offered=input_data.product_service_offered,
                lead_url=input_data.lead_url
            )
            self.logger.debug(f"Prompt for {self.name} (length: {len(formatted_prompt)}):\n{formatted_prompt[:1000]}...")


            llm_response_str = self.generate_llm_response(formatted_prompt)

            if not llm_response_str:
                self.logger.error(f"LLM call returned no response for {self.name} on lead {input_data.lead_url}")
                return DetailedApproachPlanOutput(error_message="LLM call returned no response.")

            self.logger.debug(f"LLM response received for {self.name} (length: {len(llm_response_str)}). Attempting to parse.")
            parsed_output = self.parse_llm_json_response(llm_response_str, DetailedApproachPlanOutput)
            
            if parsed_output.error_message:
                 self.logger.warning(f"{self.name} JSON parsing/validation failed for lead {input_data.lead_url}. Error: {parsed_output.error_message}. Raw response snippet: {llm_response_str[:500]}")
                 # The error message from parsing is already in parsed_output
                 return parsed_output
            
            self.logger.info(f"Successfully processed detailed approach plan for lead {input_data.lead_url}.")
            return parsed_output

        except Exception as e:
            self.logger.error(f"An unexpected error occurred in {self.name} for lead {input_data.lead_url}: {e}", exc_info=True)
            return DetailedApproachPlanOutput(error_message=f"An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    from loguru import logger # Ensure logger is available
    import sys
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")

    class MockLLMClient(LLMClientBase):
        def __init__(self, api_key: str = "mock_key"):
            super().__init__(api_key)

        def generate_text_response(self, prompt: str) -> Optional[str]:
            logger.debug(f"MockLLMClient received prompt snippet:\n{prompt[:600]}...")
            # Simulate LLM returning valid JSON based on the refined prompt
            return json.dumps({
                "main_objective": "Iniciar um diálogo consultivo com Carlos Mendes sobre otimização de eficiência na expansão da Empresa Exemplo, visando agendar uma call exploratória de 20 minutos.",
                "adapted_elevator_pitch": "Com a expansão da Empresa Exemplo, escalar operações eficientemente é vital. Nossas Soluções Incríveis de IA auxiliam empresas de TI como a sua a automatizar processos chave e otimizar recursos, garantindo crescimento sem gargalos operacionais e liberando sua equipe para inovação.",
                "contact_sequence": [
                    {
                        "step_number": 1,
                        "channel": "Email Personalizado Inicial",
                        "objective": "Obter uma resposta inicial e demonstrar entendimento dos desafios da Empresa Exemplo.",
                        "key_topics_arguments": [
                            "Reconhecer a expansão da empresa e seus desafios de escalabilidade.",
                            "Conectar expansão com desafios de escalabilidade operacional.",
                            "Mencionar como IA pode otimizar processos (ex: automatizar X, Y, Z)."
                        ],
                        "key_questions": [
                            "Carlos, com a recente expansão, como vocês estão priorizando a otimização de processos internos para sustentar esse crescimento?"
                        ],
                        "cta": "Você teria 15-20 minutos na próxima semana para uma breve conversa sobre como podemos ajudar a Empresa Exemplo a navegar por esses desafios de crescimento com mais eficiência?",
                        "supporting_materials": "Link para um estudo de caso conciso sobre IA para otimização em empresas de TI em expansão."
                    },
                    {
                        "step_number": 2,
                        "channel": "LinkedIn (Nota de Conexão)",
                        "objective": "Estabelecer conexão e reforçar a mensagem inicial de forma mais informal.",
                        "key_topics_arguments": [
                            "Referência ao email enviado.",
                            "Breve insight sobre desafios de escalar operações."
                        ],
                        "key_questions": [
                            "Carlos, vi que a Empresa Exemplo está expandindo - parabéns! Muitas empresas nesse estágio encontram desafios em [mencionar um desafio específico de otimização]. Curioso para saber como vocês estão lidando com isso. Enviei um email com algumas ideias, adoraria conectar por aqui também."
                        ],
                        "cta": "Aceitar o convite de conexão.",
                        "supporting_materials": None
                    },
                    {
                        "step_number": 3,
                        "channel": "LinkedIn (Mensagem de Follow-up)",
                        "objective": "Gerar engajamento e oferecer mais valor, caso não haja resposta ao email/convite.",
                        "key_topics_arguments": [
                            "Compartilhar artigo/insight relevante sobre otimização para empresas em expansão.",
                            "Reiterar a proposta de valor de forma sutil e consultiva."
                        ],
                        "key_questions": [],
                        "cta": "Se estiver aberto a uma conversa rápida sobre como Nossas Soluções Incríveis de IA podem endereçar alguns desses pontos, me avise quando seria um bom momento.",
                        "supporting_materials": "Link para artigo relevante ou insight."
                    }
                ],
                "engagement_indicators_to_monitor": [
                    "Abertura do email inicial e cliques no link do estudo de caso.",
                    "Aceitação do convite de conexão no LinkedIn.",
                    "Respostas às mensagens (email ou LinkedIn).",
                    "Visitas ao site da nossa empresa (se rastreável)."
                ],
                "potential_obstacles_attention_points": [
                    "Carlos Mendes pode estar extremamente ocupado devido à expansão.",
                    "Possível ceticismo em relação ao ROI real da IA ou preocupações com a complexidade da implementação.",
                    "A empresa pode já ter uma solução interna ou um fornecedor preferido."
                ],
                "suggested_next_steps_if_successful": [
                    "Agendar a call exploratória (15-20 minutos) confirmada.",
                    "Preparar perguntas específicas para a call com base nas dores e no perfil da persona.",
                    "Enviar um breve questionário de diagnóstico (1-3 perguntas) antes da call para otimizar o tempo."
                ]
            })

    logger.info("Running mock test for DetailedApproachPlanAgent...")
    mock_llm = MockLLMClient(api_key="mock_llm_key")
    agent = DetailedApproachPlanAgent(
        name="TestDetailedApproachPlanAgent",
        description="Test Agent for Detailed Approach Plan",
        llm_client=mock_llm
    )

    test_lead_analysis = "Empresa Exemplo (TI, Médio Porte). Foco em otimizar processos de desenvolvimento e QA para suportar expansão LATAM. Recentemente recebeu investimento Série B."
    test_persona_profile = "Carlos Mendes, Diretor de Operações. Responsável por eficiência operacional e adoção de novas tecnologias. Busca ROI claro e integração facilitada. Comunicação preferencial: email formal, LinkedIn para networking."
    test_deepened_pain_points = json.dumps({
        "primary_pain_category": "Eficiência Operacional",
        "detailed_pain_points": [{"pain": "Processos manuais em QA", "impact": "Atrasos nos lançamentos"}],
        "urgency_level": "High"
    })
    test_final_action_plan = json.dumps({
        "recommended_strategy_name": "Eficiência Consultiva com Foco no Impacto da Expansão LATAM",
        "primary_angle_hook": "Ajudar Carlos Mendes a garantir que a expansão LATAM da Empresa Exemplo seja suportada por operações de desenvolvimento e QA altamente eficientes e escaláveis, utilizando IA.",
        "key_talking_points": ["Otimização de QA com IA", "ROI da automação em desenvolvimento", "Suporte à expansão LATAM"],
        "communication_channel_sequence": ["Email Personalizado", "LinkedIn Connection Note", "LinkedIn Follow-up Message"],
        "tone_of_voice": "Consultivo, focado em resultados e eficiência, respeitoso ao tempo do executivo.",
        "main_call_to_action": "Agendar uma conversa exploratória de 20 minutos para discutir otimização de QA e Devops com IA.",
        "opening_question_suggestion": "Carlos, com a recente expansão para LATAM, como a Empresa Exemplo está adaptando seus ciclos de QA e desenvolvimento para garantir velocidade e qualidade?"
    })
    test_product_service = "Nossas Soluções Incríveis de IA para Automação de QA e DevOps"
    test_lead_url = "http://www.empresaexemplo.com.br"

    input_data = DetailedApproachPlanInput(
        lead_analysis=test_lead_analysis,
        persona_profile=test_persona_profile,
        deepened_pain_points=test_deepened_pain_points,
        final_action_plan_text=test_final_action_plan,
        product_service_offered=test_product_service,
        lead_url=test_lead_url
    )

    output = agent.process(input_data)

    if output.error_message:
        logger.error(f"Error: {output.error_message}")
    else:
        logger.success("DetailedApproachPlanAgent processed successfully.")
        logger.info(f"Main Objective: {output.main_objective}")
        logger.info(f"Adapted Elevator Pitch: {output.adapted_elevator_pitch}")
        logger.info(f"Contact Sequence Steps: {len(output.contact_sequence)}")
        if output.contact_sequence:
            for i, step in enumerate(output.contact_sequence):
                logger.info(f"  Step {step.step_number}: Channel: {step.channel}, Objective: {step.objective}, CTA: {step.cta}")
                logger.info(f"    Topics: {step.key_topics_arguments}")
                logger.info(f"    Questions: {step.key_questions}")
                logger.info(f"    Materials: {step.supporting_materials}")
        logger.info(f"Engagement Indicators: {output.engagement_indicators_to_monitor}")
        logger.info(f"Potential Obstacles: {output.potential_obstacles_attention_points}")
        logger.info(f"Next Steps if Successful: {output.suggested_next_steps_if_successful}")


    assert output.error_message is None
    assert "Carlos Mendes" in output.main_objective or "Empresa Exemplo" in output.main_objective
    assert len(output.contact_sequence) > 0 and output.contact_sequence[0].step_number == 1
    assert "Nossas Soluções Incríveis de IA" in output.adapted_elevator_pitch
    assert len(output.engagement_indicators_to_monitor) > 0
    assert len(output.potential_obstacles_attention_points) > 0

    logger.info("\nMock test for DetailedApproachPlanAgent completed successfully.")

```
