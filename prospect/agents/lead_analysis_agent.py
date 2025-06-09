"""
Lead Analysis Agent - Analyzes lead data to extract insights about the company.
"""

import json
from typing import Optional, Dict, Any, List
from loguru import logger

from agents.base_agent import BaseAgent
from data_models.lead_structures import (
    ValidatedLead, 
    AnalyzedLead, 
    LeadAnalysis,
    ExtractionStatus
)


class LeadAnalysisAgent(BaseAgent[ValidatedLead, AnalyzedLead]):
    """
    Agent responsible for analyzing lead data to extract:
    - Company sector and services
    - Recent activities and news
    - Potential challenges and pain points
    - Company size and culture
    - Relevance scoring
    - Opportunity fit assessment
    """
    
    def __init__(self, name: str, description: str, llm_client: Optional[object] = None, product_service_context: str = "", **kwargs):
        """
        Initialize the Lead Analysis Agent.
        
        Args:
            name: The name of the agent.
            description: A description of the agent.
            llm_client: An optional LLM client.
            product_service_context: Description of the product/service being offered
            **kwargs: Additional arguments for BaseAgent
        """
        super().__init__(name=name, description=description, llm_client=llm_client, **kwargs)
        self.product_service_context = product_service_context
    
    def process(self, input_data: ValidatedLead) -> AnalyzedLead:
        """
        Process validated lead data to generate analysis.
        
        Args:
            input_data: ValidatedLead object
            
        Returns:
            AnalyzedLead object with complete analysis
        """
        logger.info(f"Analyzing lead: {input_data.site_data.url}")
        
        # Check if extraction was successful
        if not input_data.extraction_successful:
            logger.warning(f"Lead has failed extraction, generating limited analysis")
            analysis = self._generate_limited_analysis(input_data)
        else:
            # Generate full analysis using LLM
            analysis = self._generate_full_analysis(input_data)
        
        # Create and return analyzed lead
        return AnalyzedLead(
            validated_lead=input_data,
            analysis=analysis,
            product_service_context=self.product_service_context
        )
    
    def _generate_full_analysis(self, lead: ValidatedLead) -> LeadAnalysis:
        """Generate comprehensive analysis for leads with successful extraction"""
        
        # Prepare data for LLM
        lead_data = {
            "url": str(lead.site_data.url),
            "google_search_data": lead.site_data.google_search_data.dict() if lead.site_data.google_search_data else None,
            "extracted_text_content": lead.cleaned_text_content or lead.site_data.extracted_text_content,
            "extraction_status": lead.site_data.extraction_status_message
        }
        
        prompt = self._create_analysis_prompt(lead_data)
        
        try:
            # Generate analysis using LLM
            response = self.generate_llm_response(prompt)
            
            # Try to parse as JSON first
            try:
                analysis_dict = self.parse_llm_json_response(response, None)
                return self._create_lead_analysis_from_dict(analysis_dict)
            except ValueError:
                # If JSON parsing fails, parse the text response
                return self._parse_text_analysis(response)
                
        except Exception as e:
            logger.error(f"Error generating analysis: {e}")
            # Return a basic analysis on error
            return self._generate_fallback_analysis(lead)
    
    def _generate_limited_analysis(self, lead: ValidatedLead) -> LeadAnalysis:
        """Generate limited analysis based on Google search data only"""
        
        google_data = lead.site_data.google_search_data
        
        if not google_data:
            return self._generate_fallback_analysis(lead)
        
        # Try to extract basic information from title and snippet
        title = google_data.title or ""
        snippet = google_data.snippet or ""
        
        # Simple sector detection based on keywords
        sector = self._detect_sector_from_text(f"{title} {snippet}")
        
        return LeadAnalysis(
            company_sector=sector,
            main_services=["Informação não disponível - extração falhou"],
            recent_activities=[],
            potential_challenges=[
                "Presença digital pode precisar de melhorias (site com problemas de acesso)",
                "Possível necessidade de otimização técnica do website"
            ],
            company_size_estimate="Não determinado",
            company_culture_values="Não determinado",
            relevance_score=0.3,  # Lower score due to limited data
            general_diagnosis=f"Análise limitada devido a falha na extração. Baseada apenas em: {title}",
            opportunity_fit=f"Potencial cliente para {self.product_service_context}, especialmente se precisam melhorar presença digital"
        )
    
    def _generate_fallback_analysis(self, lead: ValidatedLead) -> LeadAnalysis:
        """Generate fallback analysis when all else fails"""
        return LeadAnalysis(
            company_sector="Não identificado",
            main_services=["Não identificado"],
            recent_activities=[],
            potential_challenges=["Dados insuficientes para análise"],
            company_size_estimate="Não determinado",
            company_culture_values="Não determinado",
            relevance_score=0.1,
            general_diagnosis="Análise não disponível devido a dados insuficientes",
            opportunity_fit="Não foi possível determinar o fit com o produto/serviço"
        )
    
    def _create_analysis_prompt(self, lead_data: Dict[str, Any]) -> str:
        """Create the prompt for LLM analysis"""
        return f"""
Você é um Analista de Leads Sênior especializado em análise de empresas B2B.
Sua tarefa é analisar profundamente os dados de um lead para identificar oportunidades de negócio.

Produto/Serviço em consideração: "{self.product_service_context}"

Dados do Lead:
```json
{json.dumps(lead_data, indent=2, ensure_ascii=False)}
```

Analise os dados e forneça uma resposta ESTRUTURADA com as seguintes informações:

1. **Setor de Atuação**: Identifique o setor/indústria principal da empresa
2. **Principais Serviços/Produtos**: Liste os principais serviços ou produtos oferecidos
3. **Atividades Recentes**: Notícias, eventos, projetos ou atividades importantes mencionadas
4. **Desafios Potenciais**: Identifique possíveis dores e desafios que a empresa possa estar enfrentando
5. **Tamanho da Empresa**: Estime o porte (micro, pequena, média, grande) baseado nas informações disponíveis
6. **Cultura e Valores**: Insights sobre a cultura organizacional, se disponível
7. **Score de Relevância**: De 0 a 1, quão relevante este lead é para "{self.product_service_context}"
8. **Diagnóstico Geral**: Resumo da situação atual da empresa
9. **Fit de Oportunidade**: Como "{self.product_service_context}" pode ajudar esta empresa

Se o texto mencionar "ANÁLISE DA IMAGEM PELA IA", extraia os pontos principais dessa análise.

Formate sua resposta como um JSON válido com as seguintes chaves:
{{
    "company_sector": "string",
    "main_services": ["lista", "de", "serviços"],
    "recent_activities": ["lista", "de", "atividades"],
    "potential_challenges": ["lista", "de", "desafios"],
    "company_size_estimate": "string",
    "company_culture_values": "string",
    "relevance_score": 0.0,
    "general_diagnosis": "string",
    "opportunity_fit": "string"
}}
"""
    
    def _create_lead_analysis_from_dict(self, analysis_dict: Dict[str, Any]) -> LeadAnalysis:
        """Create LeadAnalysis object from dictionary"""
        return LeadAnalysis(
            company_sector=analysis_dict.get("company_sector", "Não identificado"),
            main_services=analysis_dict.get("main_services", ["Não identificado"]),
            recent_activities=analysis_dict.get("recent_activities", []),
            potential_challenges=analysis_dict.get("potential_challenges", []),
            company_size_estimate=analysis_dict.get("company_size_estimate"),
            company_culture_values=analysis_dict.get("company_culture_values"),
            relevance_score=float(analysis_dict.get("relevance_score", 0.5)),
            general_diagnosis=analysis_dict.get("general_diagnosis", "Análise não disponível"),
            opportunity_fit=analysis_dict.get("opportunity_fit", "Não determinado")
        )
    
    def _parse_text_analysis(self, response: str) -> LeadAnalysis:
        """Parse analysis from text response when JSON parsing fails"""
        # This is a fallback parser for non-JSON responses
        # It tries to extract information using simple text parsing
        
        logger.warning("Falling back to text parsing for analysis")
        
        # Default values
        sector = "Não identificado"
        services = ["Não identificado"]
        activities = []
        challenges = []
        size = "Não determinado"
        culture = "Não determinado"
        score = 0.5
        diagnosis = "Análise extraída de texto não estruturado"
        fit = "Análise disponível no diagnóstico"
        
        # Try to extract sector
        if "setor:" in response.lower() or "setor de atuação:" in response.lower():
            try:
                sector_start = response.lower().find("setor")
                sector_line = response[sector_start:].split('\n')[0]
                sector = sector_line.split(':', 1)[1].strip()
            except:
                pass
        
        # Try to extract relevance score
        if "score" in response.lower() or "relevância" in response.lower():
            import re
            score_match = re.search(r'(\d+\.?\d*)', response[response.lower().find("score"):])
            if score_match:
                try:
                    score = float(score_match.group(1))
                    if score > 1:  # Probably percentage
                        score = score / 100
                except:
                    pass
        
        # Use the full response as diagnosis if we couldn't parse properly
        if len(response) > 100:
            diagnosis = response[:500] + "..." if len(response) > 500 else response
        
        return LeadAnalysis(
            company_sector=sector,
            main_services=services,
            recent_activities=activities,
            potential_challenges=challenges,
            company_size_estimate=size,
            company_culture_values=culture,
            relevance_score=score,
            general_diagnosis=diagnosis,
            opportunity_fit=fit
        )
    
    def _detect_sector_from_text(self, text: str) -> str:
        """Simple sector detection based on keywords"""
        text_lower = text.lower()
        
        sector_keywords = {
            "Tecnologia": ["software", "tecnologia", "tech", "ti", "sistema", "app", "digital"],
            "Advocacia": ["advocacia", "advogado", "jurídico", "direito", "escritório de advocacia"],
            "Saúde": ["saúde", "médico", "hospital", "clínica", "farmácia", "medicina"],
            "Educação": ["educação", "escola", "universidade", "curso", "ensino", "faculdade"],
            "Comércio": ["loja", "varejo", "comércio", "venda", "magazine", "shopping"],
            "Indústria": ["indústria", "fábrica", "manufatura", "produção", "industrial"],
            "Serviços": ["serviço", "consultoria", "agência", "prestador"],
            "Alimentação": ["restaurante", "alimentação", "comida", "bebida", "alimento"],
            "Construção": ["construção", "engenharia", "obra", "empreiteira", "construtora"],
            "Imobiliário": ["imobiliária", "imóvel", "corretora", "real estate"]
        }
        
        for sector, keywords in sector_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return sector
        
        return "Outros" 