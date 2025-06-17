from enum import Enum

class ProcessingStage(str, Enum):
    PROSPECTING = 'prospecting'
    LEAD_QUALIFICATION = 'lead_qualification'
    ANALYZING_REFINING = 'analyzing_refining'
    POSSIBLY_QUALIFIED = 'possibly_qualified'
    REVISANDO = 'revisando'
    PRIMEIRAS_MENSAGENS = 'primeiras_mensagens'
    NEGOCIANDO = 'negociando'
    REUNIAO_AGENDADA = 'reuniao_agendada'
    DESQUALIFICADO = 'desqualificado'
    INTAKE = 'intake'
    ANALYSIS = 'analysis'
    PERSONA = 'persona'
    STRATEGY = 'strategy'
    MESSAGE = 'message'
    COMPLETED = 'completed'

class LeadStatus(str, Enum):
    LEAD_GENERATED = 'LEAD_GENERATED'
    INTAKE_VALIDATED = 'INTAKE_VALIDATED'
    ANALYSIS_COMPLETE = 'ANALYSIS_COMPLETE'
    ENRICHMENT_STARTED = 'ENRICHMENT_STARTED'
    ENRICHMENT_COMPLETE = 'ENRICHMENT_COMPLETE'
    PIPELINE_FAILED = 'PIPELINE_FAILED'

class QualificationTier(str, Enum):
    TIER_1_IDEAL_FIT = 'Tier 1: Ideal Fit'
    TIER_2_GOOD_FIT = 'Tier 2: Good Fit'
    TIER_3_POTENTIAL_FIT = 'Tier 3: Potential Fit'
    TIER_4_LOW_PRIORITY = 'Tier 4: Low Priority'
    NOT_QUALIFIED = 'Not Qualified'

class ExtractionStatus(str, Enum):
    """Status of website content extraction"""
    SUCCESS = "SUCESSO NA EXTRAÇÃO"
    SUCCESS_VIA_IMAGE = "SUCESSO NA EXTRAÇÃO (VIA ANÁLISE DE IMAGEM)"
    FAILED_TIMEOUT = "FALHA NA EXTRAÇÃO: TIMEOUT NA NAVEGAÇÃO"
    FAILED_STATUS = "FALHA NA EXTRAÇÃO: Página retornou status"
    FAILED_OTHER = "FALHA NA EXTRAÇÃO"

class CommunicationChannel(str, Enum):
    """Preferred communication channels"""
    EMAIL = "email"
    LINKEDIN = "linkedin"
    WHATSAPP = "whatsapp"
    PHONE = "phone"
