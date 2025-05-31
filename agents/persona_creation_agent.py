"""
Persona Creation Agent for Nellia Prospector
Creates detailed decision-maker personas for analyzed leads.
"""

from typing import List, Optional
from datetime import datetime
from loguru import logger

from data_models.lead_structures import (
    AnalyzedLead, 
    LeadWithPersona, 
    PersonaDetails
)
from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClient


class PersonaCreationAgent(BaseAgent):
    """Agent responsible for creating decision-maker personas for leads"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        super().__init__(agent_name="PersonaCreationAgent")
        self.llm_client = llm_client or LLMClient()
        
    def execute(self, analyzed_lead: AnalyzedLead) -> LeadWithPersona:
        """
        Create a detailed persona for the analyzed lead
        
        Args:
            analyzed_lead: AnalyzedLead with company analysis
            
        Returns:
            LeadWithPersona with persona details
        """
        self.start_execution()
        
        try:
            logger.info(f"Creating persona for lead: {analyzed_lead.validated_lead.site_data.url}")
            
            # Create persona using LLM
            persona = self._create_persona(analyzed_lead)
            
            # Build result
            result = LeadWithPersona(
                analyzed_lead=analyzed_lead,
                persona=persona,
                persona_creation_timestamp=datetime.now()
            )
            
            self.end_execution(success=True)
            logger.info(f"Persona created: {persona.fictional_name} ({persona.likely_role})")
            
            return result
            
        except Exception as e:
            self.end_execution(success=False, error=str(e))
            logger.error(f"Error creating persona: {e}")
            raise
    
    def _create_persona(self, analyzed_lead: AnalyzedLead) -> PersonaDetails:
        """Create persona using LLM analysis"""
        
        # Prepare context for LLM
        company_info = {
            "url": str(analyzed_lead.validated_lead.site_data.url),
            "sector": analyzed_lead.analysis.company_sector,
            "services": analyzed_lead.analysis.main_services,
            "challenges": analyzed_lead.analysis.potential_challenges,
            "company_size": analyzed_lead.analysis.company_size_estimate,
            "culture": analyzed_lead.analysis.company_culture_values,
            "diagnosis": analyzed_lead.analysis.general_diagnosis
        }
        
        prompt = self._build_persona_prompt(company_info)
        
        # Get LLM response
        response = self.llm_client.generate_text(prompt)
        
        # Parse response into PersonaDetails
        return self._parse_persona_response(response)
    
    def _build_persona_prompt(self, company_info: dict) -> str:
        """Build the prompt for persona creation"""
        
        return f"""
Você é um Especialista em Desenvolvimento de Personas B2B.
Sua tarefa é criar uma persona detalhada do tomador de decisão ideal dentro da empresa analisada.

INFORMAÇÕES DA EMPRESA:
- URL: {company_info['url']}
- Setor: {company_info['sector']}
- Principais serviços: {', '.join(company_info['services'])}
- Desafios identificados: {', '.join(company_info['challenges'])}
- Tamanho estimado: {company_info.get('company_size', 'Não determinado')}
- Cultura: {company_info.get('culture', 'Não determinada')}
- Diagnóstico: {company_info['diagnosis']}

INSTRUÇÕES:
Crie uma persona específica para um tomador de decisão chave desta empresa. Responda no formato JSON com as seguintes chaves:

{{
    "fictional_name": "Nome fictício e realista",
    "likely_role": "Cargo/função provável (ex: CEO, Diretor Comercial, Gerente de TI)",
    "key_responsibilities": ["responsabilidade1", "responsabilidade2", "responsabilidade3"],
    "professional_goals": ["objetivo1", "objetivo2", "objetivo3"],
    "main_challenges": ["desafio1", "desafio2", "desafio3"],
    "motivations": ["motivação1", "motivação2", "motivação3"],
    "solution_seeking": "O que esta pessoa busca em soluções",
    "communication_style": "Estilo de comunicação preferido",
    "decision_making_process": "Como toma decisões de compra/investimento"
}}

DIRETRIZES:
- Base a persona no setor e características identificadas da empresa
- Seja específico e realista para o contexto brasileiro
- Considere o nível hierárquico apropriado para o tamanho da empresa
- Foque em aspectos que influenciam decisões de compra
- Use linguagem profissional e precisa

Responda APENAS com o JSON válido, sem explicações adicionais.
"""
    
    def _parse_persona_response(self, response: str) -> PersonaDetails:
        """Parse LLM response into PersonaDetails"""
        
        try:
            import json
            
            # Clean response and extract JSON
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            data = json.loads(response)
            
            return PersonaDetails(
                fictional_name=data.get('fictional_name', 'João Silva'),
                likely_role=data.get('likely_role', 'Tomador de Decisão'),
                key_responsibilities=data.get('key_responsibilities', ['Responsabilidades não especificadas']),
                professional_goals=data.get('professional_goals', ['Objetivos não especificados']),
                main_challenges=data.get('main_challenges', ['Desafios não especificados']),
                motivations=data.get('motivations', ['Motivações não especificadas']),
                solution_seeking=data.get('solution_seeking', 'Soluções eficazes para desafios empresariais'),
                communication_style=data.get('communication_style', 'Profissional e direto'),
                decision_making_process=data.get('decision_making_process', 'Processo não especificado')
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse persona JSON response: {e}")
            # Return fallback persona
            return PersonaDetails(
                fictional_name="João Silva",
                likely_role="Tomador de Decisão",
                key_responsibilities=["Tomar decisões estratégicas"],
                professional_goals=["Melhorar eficiência operacional"],
                main_challenges=["Otimização de processos"],
                motivations=["Crescimento da empresa"],
                solution_seeking="Soluções práticas e eficazes",
                communication_style="Profissional e objetivo",
                decision_making_process="Análise cuidadosa de ROI e benefícios"
            )
        
        except Exception as e:
            logger.error(f"Error parsing persona response: {e}")
            raise
