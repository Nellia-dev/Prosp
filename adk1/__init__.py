# project/adk/__init__.py

"""
Prospecter: An intelligent AI agent system for lead generation.
This package contains the definitions for various specialized agents and their tools.
"""

# Importa o agente principal que será o ponto de entrada para o refinamento de queries.
# Conforme sua solicitação, 'root_agent' agora é um alias para o agente de refinamento.
from .agent import root_agent

# Importa os outros agentes especializados para que o orquestrador (run.py) possa acessá-los.
from .agent import (
    lead_search_and_qualify_agent,
    structured_lead_extractor_agent,
    direct_url_lead_processor_agent
)
