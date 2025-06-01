"""
Persona Creation Agent for Nellia Prospector
Creates detailed decision-maker personas for analyzed leads.
"""

from typing import Optional
from datetime import datetime
from loguru import logger
import json

from data_models.lead_structures import (
    AnalyzedLead, 
    LeadWithPersona, 
    PersonaDetails
)
from agents.base_agent import BaseAgent
from core_logic.llm_client import LLMClientBase

class PersonaCreationAgent(BaseAgent[AnalyzedLead, LeadWithPersona]):
    """Agent responsible for creating decision-maker personas for leads"""
    
    def __init__(self, llm_client: Optional[LLMClientBase] = None):
        super().__init__(
            name="PersonaCreationAgent",
            description="Creates detailed decision-maker personas for B2B leads",
            llm_client=llm_client
        )
        
    def process(self, analyzed_lead: AnalyzedLead) -> LeadWithPersona:
        """
        Create a detailed persona for the analyzed lead
        
        Args:
            analyzed_lead: AnalyzedLead with company analysis
            
        Returns:
            LeadWithPersona with persona details
        """
        logger.info(f"Creating persona for: {analyzed_lead.validated_lead.site_data.url}")
        
        # Build the prompt for persona creation
        prompt = self._build_persona_prompt(analyzed_lead)
        
        # Generate LLM response
        response = self.generate_llm_response(prompt)
        
        # Parse the response
        persona_data = self.parse_llm_json_response(response, None)
        
        # Create PersonaDetails from parsed data
        persona = self._create_persona_details(persona_data)
        
        # Build and return result
        result = LeadWithPersona(
            analyzed_lead=analyzed_lead,
            persona=persona,
            persona_creation_timestamp=datetime.now()
        )
        
        logger.info(f"Persona created: {persona.fictional_name} ({persona.likely_role})")
        return result
    
    def _build_persona_prompt(self, analyzed_lead: AnalyzedLead) -> str:
        """Build the prompt for persona creation"""
        
        analysis = analyzed_lead.analysis
        company_info = {
            "url": str(analyzed_lead.validated_lead.site_data.url),
            "sector": analysis.company_sector,
            "services": analysis.main_services,
            "challenges": analysis.potential_challenges,
            "company_size": analysis.company_size_estimate or "Não determinado",
            "culture": analysis.company_culture_values or "Não determinada",
            "diagnosis": analysis.general_diagnosis
        }
        
        return f"""Você é um Especialista em Desenvolvimento de Personas B2B para o mercado brasileiro.
Sua tarefa é criar uma persona detalhada do tomador de decisão ideal dentro da empresa analisada.

INFORMAÇÕES DA EMPRESA:
- URL: {company_info['url']}
- Setor: {company_info['sector']}
- Principais serviços: {', '.join(company_info['services'])}
- Desafios identificados: {', '.join(company_info['challenges'])}
- Tamanho estimado: {company_info['company_size']}
- Cultura: {company_info['culture']}
- Diagnóstico: {company_info['diagnosis']}

CONTEXTO DO MERCADO BRASILEIRO:
- Considere hierarquia e formalidade nas relações empresariais
- Decisões muitas vezes envolvem múltiplos stakeholders
- Relacionamento é fundamental antes do negócio
- Preferência por comunicação direta mas respeitosa

INSTRUÇÕES:
Crie uma persona específica para um tomador de decisão chave desta empresa. 
Considere o setor, tamanho da empresa e cultura identificados.

Responda APENAS com JSON válido no seguinte formato:
{{
    "fictional_name": "Nome fictício e realista brasileiro",
    "likely_role": "Cargo/função provável (ex: CEO, Diretor Comercial, Gerente de TI)",
    "key_responsibilities": ["responsabilidade1", "responsabilidade2", "responsabilidade3"],
    "professional_goals": ["objetivo1", "objetivo2", "objetivo3"],
    "main_challenges": ["desafio1", "desafio2", "desafio3"],
    "motivations": ["motivação1", "motivação2", "motivação3"],
    "solution_seeking": "O que esta persona busca em soluções",
    "communication_style": "Estilo de comunicação preferido (formal/informal, técnico/comercial)",
    "decision_making_process": "Como toma decisões de compra/investimento"
}}

DIRETRIZES:
- Base a persona no setor e características identificadas da empresa
- Seja específico e realista para o contexto brasileiro
- Considere o nível hierárquico apropriado para o tamanho da empresa
- Foque em aspectos que influenciam decisões de compra B2B
- Use linguagem profissional e precisa"""
    
    def _create_persona_details(self, persona_data: dict) -> PersonaDetails:
        """Create PersonaDetails from parsed JSON data"""
        
        try:
            return PersonaDetails(
                fictional_name=persona_data.get('fictional_name', 'João Silva'),
                likely_role=persona_data.get('likely_role', 'Tomador de Decisão'),
                key_responsibilities=persona_data.get('key_responsibilities', ['Responsabilidades não especificadas']),
                professional_goals=persona_data.get('professional_goals', ['Objetivos não especificados']),
                main_challenges=persona_data.get('main_challenges', ['Desafios não especificados']),
                motivations=persona_data.get('motivations', ['Motivações não especificadas']),
                solution_seeking=persona_data.get('solution_seeking', 'Soluções eficazes para desafios empresariais'),
                communication_style=persona_data.get('communication_style', 'Profissional e direto'),
                decision_making_process=persona_data.get('decision_making_process', 'Processo não especificado')
            )
            
        except Exception as e:
            logger.warning(f"Failed to create persona from data: {e}")
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
