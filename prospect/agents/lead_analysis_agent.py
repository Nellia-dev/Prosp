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
        
        # Check if we have sufficient content for full analysis
        has_content = (
            input_data.extraction_successful and
            (input_data.cleaned_text_content or input_data.site_data.extracted_text_content)
        ) or (
            input_data.site_data.google_search_data and
            input_data.site_data.google_search_data.snippet
        )
        
        if not has_content:
            logger.warning(f"Lead has insufficient data for full analysis, generating limited analysis")
            analysis = self._generate_limited_analysis(input_data)
        else:
            logger.info(f"Lead has sufficient data for full analysis")
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
        lead_data_for_prompt = {
            "url": str(lead.site_data.url),
            "google_search_snippet": lead.site_data.google_search_data.snippet if lead.site_data.google_search_data else None,
            "google_search_title": lead.site_data.google_search_data.title if lead.site_data.google_search_data else None,
            "extracted_web_content": lead.cleaned_text_content or lead.site_data.extracted_text_content, # Prioritize cleaned text
            "extraction_status_message": lead.site_data.extraction_status_message,
            "extraction_successful": lead.extraction_successful
        }
        
        prompt = self._create_analysis_prompt(lead_data_for_prompt)
        
        try:
            # Generate analysis using LLM
            response_text = self.generate_llm_response(prompt)
            
            # Try to parse as JSON first
            try:
                # The parse_llm_json_response method should handle potential markdown ```json ... ```
                analysis_dict = self.parse_llm_json_response(response_text, None)
                if analysis_dict is None: # If parse_llm_json_response returns None due to parsing issue
                    logger.warning("LLM response was not valid JSON after attempting to parse. Falling back to text parsing.")
                    analysis_dict = self._parse_text_analysis_to_dict(response_text) # Try text parsing to dict
                return self._create_lead_analysis_from_dict(analysis_dict)
            except ValueError as ve: # Catch explicit JSON parsing errors if parse_llm_json_response raises it
                logger.warning(f"JSON parsing failed with ValueError: {ve}. Falling back to text parsing.")
                analysis_dict = self._parse_text_analysis_to_dict(response_text) # Try text parsing to dict
                return self._create_lead_analysis_from_dict(analysis_dict)
                
        except Exception as e:
            logger.error(f"Error generating analysis for {lead.site_data.url}: {e}", exc_info=True)
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
            opportunity_fit=f"Avaliar com cautela. Se o {self.product_service_context} resolve problemas de presença digital ou dependência de dados de site, pode haver oportunidade."
        )
    
    def _generate_fallback_analysis(self, lead: ValidatedLead) -> LeadAnalysis:
        """Generate fallback analysis when all else fails"""
        return LeadAnalysis(
            company_sector="Não Identificado",
            main_services=["Não Identificado"],
            recent_activities=[],
            potential_challenges=["Dados insuficientes para análise detalhada."],
            company_size_estimate="Não Determinado",
            company_culture_values="Não Determinado",
            relevance_score=0.1, # Minimal score for fallback
            general_diagnosis="Análise não pôde ser realizada devido a dados insuficientes ou erro no processamento.",
            opportunity_fit="Não foi possível determinar o fit com o produto/serviço devido à falta de dados."
        )
    
    def _create_analysis_prompt(self, lead_data_for_prompt: Dict[str, Any]) -> str:
        """
        Create the prompt for LLM analysis.
        Refined prompt to improve JSON adherence and provide clearer field guidance.
        """
        # Prepare lead_data JSON string for embedding in the prompt
        # Ensure ensure_ascii=False for proper handling of non-ASCII characters
        lead_data_json_str = json.dumps(lead_data_for_prompt, indent=2, ensure_ascii=False)

        # Updated prompt with more explicit instructions for JSON output and field definitions
        return f"""
Você é um Analista de Inteligência de Mercado Sênior, especializado em avaliar empresas B2B para identificar potenciais clientes.
Sua principal tarefa é analisar os dados fornecidos sobre um lead e retornar uma avaliação estruturada em formato JSON.

Nosso produto/serviço é: "{self.product_service_context}"

Analise os seguintes dados do lead:
```json
{lead_data_json_str}
```

INSTRUÇÕES DE SAÍDA:
Responda EXCLUSIVAMENTE com um objeto JSON válido, seguindo o schema e as descrições de campo abaixo.
NÃO inclua NENHUM texto, explicação, ou markdown (como ```json) antes ou depois do objeto JSON.
A sua resposta deve ser apenas o JSON em si.

SCHEMA JSON ESPERADO E DESCRIÇÃO DOS CAMPOS:
{{
    "company_sector": "string | null - O setor/indústria principal da empresa (ex: 'Tecnologia SaaS', 'Varejo de Moda', 'Consultoria Financeira'). Se não puder determinar com base no texto, use 'Não Especificado'.",
    "main_services": ["string", ...] - Lista dos principais serviços ou produtos oferecidos pela empresa. Extraia do texto. Se não encontrar informações claras, use uma lista vazia [].",
    "recent_activities": ["string", ...] - Lista de notícias, eventos, lançamentos de produtos, parcerias ou outras atividades e marcos importantes recentes (idealmente dos últimos 6-12 meses) mencionados no texto. Se não encontrar, use uma lista vazia [].",
    "potential_challenges": ["string", ...] - Lista de possíveis dores, desafios ou problemas que a empresa pode estar enfrentando, inferidos a partir do texto fornecido. Se não encontrar, use uma lista vazia [].",
    "company_size_estimate": "string | null - Estimativa do porte da empresa (ex: 'Micro (1-9 funcionários)', 'Pequena (10-49 funcionários)', 'Média (50-249 funcionários)', 'Grande (250+ funcionários)'). Infire com base em pistas no texto; se impossível, use 'Não Determinado'.",
    "company_culture_values": "string | null - Insights sobre a cultura organizacional, missão, visão ou valores da empresa, se explicitamente mencionados ou fortemente implícitos no texto. Se não encontrar, use 'Não foi possível determinar'.",
    "relevance_score": "float - Um score numérico entre 0.0 e 1.0 indicando o quão relevante este lead é para o nosso produto/serviço '{self.product_service_context}'. Considere 0.0 como totalmente irrelevante e 1.0 como perfeitamente alinhado. Baseie-se nos desafios, serviços e setor da empresa. Seja crítico e objetivo.",
    "general_diagnosis": "string | null - Um resumo conciso (2-3 frases) da situação atual da empresa, seus pontos fortes e fracos percebidos com base nos dados. Se o campo 'extracted_web_content' nos dados do lead contiver menção a 'ANÁLISE DA IMAGEM PELA IA', incorpore os achados relevantes dessa análise aqui. Se não houver conteúdo suficiente para um diagnóstico, use 'Diagnóstico limitado devido à insuficiência de dados.'.",
    "opportunity_fit": "string | null - Explique brevemente (2-3 frases) como nosso produto/serviço '{self.product_service_context}' poderia especificamente ajudar esta empresa, conectando com os 'potential_challenges' ou necessidades identificadas. Justifique o 'relevance_score'. Se não houver fit claro, indique explicitamente."
}}

INSTRUÇÕES ADICIONAIS IMPORTANTES:
- PREENCHA TODOS OS CAMPOS do JSON conforme o schema.
- Para campos string opcionais (marcados com `| null`), se a informação não for encontrada, use o valor string padrão indicado na descrição (ex: 'Não Especificado', 'Não Determinado') ou, se preferir e o schema permitir implicitamente `null` através da descrição, pode usar `null`. No entanto, para este exercício, prefira as strings padrão como 'Não Especificado'.
- Para campos de lista (ex: `main_services`), se nenhuma informação for encontrada, OBRIGATORIAMENTE retorne uma lista vazia `[]`.
- Seja objetivo e baseie sua análise ESTRITAMENTE nas informações fornecidas nos "Dados do Lead". NÃO INVENTE informações não presentes no texto.
- A sua resposta final deve ser APENAS o objeto JSON.
"""
    
    def _create_lead_analysis_from_dict(self, analysis_dict: Optional[Dict[str, Any]]) -> LeadAnalysis:
        """Create LeadAnalysis object from dictionary, handling potential None dictionary."""
        if analysis_dict is None:
            logger.warning("Received None for analysis_dict, creating a fallback LeadAnalysis.")
            # Create a LeadAnalysis that indicates failure or insufficient data.
            # This structure should mirror _generate_fallback_analysis or similar.
            return LeadAnalysis(
                company_sector="Não Identificado (erro de parsing)",
                main_services=["Não Identificado (erro de parsing)"],
                relevance_score=0.0,
                general_diagnosis="Falha ao processar a resposta do LLM ou dados insuficientes.",
                opportunity_fit="Não foi possível determinar o fit devido a erro de parsing."
            )

        return LeadAnalysis(
            company_sector=analysis_dict.get("company_sector", "Não Especificado"),
            main_services=analysis_dict.get("main_services") if isinstance(analysis_dict.get("main_services"), list) else ["Não Identificado"],
            recent_activities=analysis_dict.get("recent_activities") if isinstance(analysis_dict.get("recent_activities"), list) else [],
            potential_challenges=analysis_dict.get("potential_challenges") if isinstance(analysis_dict.get("potential_challenges"), list) else [],
            company_size_estimate=analysis_dict.get("company_size_estimate", "Não Determinado"),
            company_culture_values=analysis_dict.get("company_culture_values", "Não foi possível determinar"),
            relevance_score=float(analysis_dict.get("relevance_score", 0.0)), # Ensure float
            general_diagnosis=analysis_dict.get("general_diagnosis", "Análise não disponível"),
            opportunity_fit=analysis_dict.get("opportunity_fit", "Não determinado")
        )
    
    def _parse_text_analysis_to_dict(self, response_text: str) -> Dict[str, Any]:
        """
        Rudimentary fallback to parse key information from text if JSON fails.
        This aims to populate a dictionary similar to what the JSON parser would.
        """
        logger.warning("Attempting rudimentary text parsing for analysis as JSON parsing failed.")
        analysis_dict = {}
        response_lower = response_text.lower()

        # Simplified extraction - this is very basic and error-prone
        # It's better to improve the prompt to ensure JSON output

        def extract_value(key_pattern: str, text: str, text_lower: str) -> Optional[str]:
            try:
                match = re.search(f"{key_pattern}\\s*:\\s*(.+)", text, re.IGNORECASE)
                if match:
                    return match.group(1).strip().split('\n')[0] # Take first line after key
            except Exception:
                pass # Ignore regex errors
            return None

        analysis_dict["company_sector"] = extract_value("company_sector", response_text, response_lower) or \
                                          extract_value("setor de atuação", response_text, response_lower) or \
                                          "Não Especificado (fallback)"
        
        # For lists, this is even harder with simple regex from unstructured text
        analysis_dict["main_services"] = [] # Default to empty list
        analysis_dict["recent_activities"] = []
        analysis_dict["potential_challenges"] = []

        analysis_dict["company_size_estimate"] = extract_value("company_size_estimate", response_text, response_lower) or \
                                                 extract_value("tamanho da empresa", response_text, response_lower) or \
                                                 "Não Determinado (fallback)"
        
        analysis_dict["company_culture_values"] = extract_value("company_culture_values", response_text, response_lower) or \
                                                  extract_value("cultura e valores", response_text, response_lower) or \
                                                  "Não foi possível determinar (fallback)"
        
        score_str = extract_value("relevance_score", response_text, response_lower) or \
                      extract_value("score de relevância", response_text, response_lower)
        if score_str:
            try:
                analysis_dict["relevance_score"] = float(re.search(r"(\d\.?\d*)", score_str).group(1))
            except:
                analysis_dict["relevance_score"] = 0.1 # Fallback score
        else:
            analysis_dict["relevance_score"] = 0.1

        analysis_dict["general_diagnosis"] = extract_value("general_diagnosis", response_text, response_lower) or \
                                             extract_value("diagnóstico geral", response_text, response_lower) or \
                                             "Diagnóstico limitado (fallback de parsing)"
        
        analysis_dict["opportunity_fit"] = extract_value("opportunity_fit", response_text, response_lower) or \
                                           extract_value("fit de oportunidade", response_text, response_lower) or \
                                           "Fit não determinado (fallback de parsing)"
        
        logger.debug(f"Rudimentary text parsing extracted: {analysis_dict}")
        return analysis_dict

    # This method is kept as it's used by _generate_limited_analysis
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