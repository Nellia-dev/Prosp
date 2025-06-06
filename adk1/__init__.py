# project/adk/__init__.py

from .agent import root_agent # <-- Esta linha é crucial!

# Se você quiser que os outros agentes também sejam importáveis diretamente de 'adk',
# você pode adicioná-los aqui, mas o sistema ADK principal só procura por 'root_agent'.
# from .agent import query_builder_agent, search_executor_agent
