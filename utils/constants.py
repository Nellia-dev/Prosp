"""
Constants and configuration values for Nellia Prospector
Centralized location for all project constants.
"""

from enum import Enum

# Processing Constants
MAX_TEXT_LENGTH = 15000
MAX_LEADS_PER_BATCH = 100
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 8192
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 5

# Brazilian Business Constants
BRAZILIAN_BUSINESS_HOURS = {
    "start": 9,  # 9 AM
    "end": 18,   # 6 PM
    "lunch_start": 12,  # 12 PM
    "lunch_end": 14     # 2 PM
}

BRAZILIAN_HOLIDAYS = [
    "01-01",  # New Year
    "04-21",  # Tiradentes
    "09-07",  # Independence Day
    "10-12",  # Our Lady of Aparecida
    "11-02",  # All Souls' Day
    "11-15",  # Proclamation of the Republic
    "12-25",  # Christmas
]

# ROI and Performance Targets
TARGET_ROI_INCREASE = 5.27  # 527% increase
TARGET_RESPONSE_RATE = 0.15  # 15%
TARGET_CONVERSION_RATE = 0.05  # 5%
MIN_RELEVANCE_SCORE = 0.7
MIN_QUALIFICATION_SCORE = 0.6

# Brazilian Business Culture Keywords
BRAZILIAN_BUSINESS_INDICATORS = [
    "brasil", "brazil", "brasileiro", "brasileira",
    "são paulo", "sp", "rio de janeiro", "rj",
    "belo horizonte", "bh", "brasília", "salvador",
    "cnpj", "cpf", "mei", "ltda", "s.a.",
    "anvisa", "receita federal", "sefaz"
]

# Industry Sector Classifications
SECTOR_KEYWORDS = {
    "tecnologia": [
        "software", "tecnologia", "tech", "ti", "sistema", "app", 
        "digital", "desenvolvimento", "programação", "dados", "ia",
        "inteligência artificial", "machine learning", "cloud"
    ],
    "advocacia": [
        "advocacia", "advogado", "jurídico", "direito", 
        "escritório de advocacia", "legal", "tribunal", "justiça"
    ],
    "saúde": [
        "saúde", "médico", "hospital", "clínica", "farmácia", 
        "medicina", "enfermagem", "fisioterapia", "odontologia"
    ],
    "educação": [
        "educação", "escola", "universidade", "curso", "ensino", 
        "faculdade", "treinamento", "capacitação", "e-learning"
    ],
    "comércio": [
        "loja", "varejo", "comércio", "venda", "magazine", 
        "shopping", "e-commerce", "marketplace"
    ],
    "indústria": [
        "indústria", "fábrica", "manufatura", "produção", 
        "industrial", "automação", "metalúrgica", "têxtil"
    ],
    "serviços": [
        "serviço", "consultoria", "agência", "prestador", 
        "assessoria", "terceirização"
    ],
    "alimentação": [
        "restaurante", "alimentação", "comida", "bebida", 
        "alimento", "gastronomia", "delivery", "food"
    ],
    "construção": [
        "construção", "engenharia", "obra", "empreiteira", 
        "construtora", "arquitetura", "reforma"
    ],
    "imobiliário": [
        "imobiliária", "imóvel", "corretora", "real estate", 
        "aluguel", "venda", "apartamento", "casa"
    ],
    "logística": [
        "logística", "transporte", "frete", "distribuição", 
        "armazenagem", "expedição", "supply chain"
    ],
    "financeiro": [
        "banco", "financeiro", "crédito", "empréstimo", 
        "investimento", "seguros", "fintech", "pagamento"
    ]
}

# LLM Provider Settings
class LLMProvider(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash-latest"
DEFAULT_OPENAI_MODEL = "gpt-4"
FALLBACK_MODEL_GEMINI = "gemini-1.5-flash"
FALLBACK_MODEL_OPENAI = "gpt-3.5-turbo"

# Communication Channels
class CommunicationChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin" 
    WHATSAPP = "whatsapp"
    PHONE = "phone"

CHANNEL_LIMITS = {
    CommunicationChannel.EMAIL: {
        "subject_max_chars": 50,
        "body_max_words": 150,
        "recommended_words": 100
    },
    CommunicationChannel.LINKEDIN: {
        "message_max_chars": 300,
        "recommended_chars": 200
    },
    CommunicationChannel.WHATSAPP: {
        "message_max_chars": 500,
        "recommended_chars": 300
    },
    CommunicationChannel.PHONE: {
        "script_max_words": 200,
        "recommended_words": 150
    }
}

# Processing Status Values
class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"

class ExtractionStatus(str, Enum):
    SUCCESS = "SUCESSO NA EXTRAÇÃO"
    SUCCESS_VIA_IMAGE = "SUCESSO NA EXTRAÇÃO (VIA ANÁLISE DE IMAGEM)"
    FAILED_TIMEOUT = "FALHA NA EXTRAÇÃO: TIMEOUT NA NAVEGAÇÃO"
    FAILED_STATUS = "FALHA NA EXTRAÇÃO: Página retornou status"
    FAILED_OTHER = "FALHA NA EXTRAÇÃO"

# Qualification Tiers
class QualificationTier(str, Enum):
    HIGH_POTENTIAL = "High Potential"
    MEDIUM_POTENTIAL = "Medium Potential"
    LOW_POTENTIAL = "Low Potential"
    NOT_QUALIFIED = "Not Qualified"

QUALIFICATION_THRESHOLDS = {
    QualificationTier.HIGH_POTENTIAL: 0.8,
    QualificationTier.MEDIUM_POTENTIAL: 0.6,
    QualificationTier.LOW_POTENTIAL: 0.4,
    QualificationTier.NOT_QUALIFIED: 0.0
}

# Urgency Levels
class UrgencyLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

URGENCY_WEIGHTS = {
    UrgencyLevel.CRITICAL: 0.4,
    UrgencyLevel.HIGH: 0.3,
    UrgencyLevel.MEDIUM: 0.2,
    UrgencyLevel.LOW: 0.1
}

# File and Export Settings
EXPORT_FORMATS = ["json", "csv", "xlsx"]
MAX_EXPORT_RECORDS = 10000
BACKUP_RETENTION_DAYS = 30

# Rate Limiting
TAVILY_MAX_REQUESTS_PER_MINUTE = 60
TAVILY_MAX_RESULTS = 3
GEMINI_MAX_REQUESTS_PER_MINUTE = 60
OPENAI_MAX_REQUESTS_PER_MINUTE = 60

# Error Messages
ERROR_MESSAGES = {
    "missing_api_key": "API key not found. Please check your environment variables.",
    "rate_limit_exceeded": "Rate limit exceeded. Please wait before retrying.",
    "invalid_input": "Invalid input data provided.",
    "processing_failed": "Processing failed due to an unexpected error.",
    "no_leads_found": "No valid leads found in the input data.",
    "extraction_failed": "Failed to extract content from website.",
    "llm_error": "Error communicating with language model.",
    "validation_error": "Data validation failed."
}

# Success Messages
SUCCESS_MESSAGES = {
    "processing_complete": "Lead processing completed successfully.",
    "export_complete": "Data exported successfully.",
    "validation_passed": "All data validation checks passed.",
    "agent_initialized": "Agent initialized successfully."
}

# Debug and Logging
LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# Monitoring and Metrics
METRICS_COLLECTION_ENABLED = True
PERFORMANCE_THRESHOLDS = {
    "max_processing_time_per_lead": 180,  # 3 minutes
    "max_memory_usage_mb": 1024,  # 1GB
    "min_success_rate": 0.8,  # 80%
    "max_error_rate": 0.2  # 20%
}

# Nellia-specific USPs and Value Propositions
NELLIA_USPS = {
    "ai_powered_lead_processing": {
        "claim": "527% ROI increase through AI-powered lead processing",
        "proof_points": ["Automated analysis", "Personalized outreach", "Higher conversion rates"]
    },
    "brazilian_market_expertise": {
        "claim": "Deep Brazilian market understanding",
        "proof_points": ["Portuguese-native team", "LGPD compliance", "Regional insights"]
    },
    "personalized_outreach_automation": {
        "claim": "15x faster lead processing with personalization",
        "proof_points": ["AI-generated personas", "Custom messaging", "Multi-channel approach"]
    },
    "data_driven_optimization": {
        "claim": "85% lead qualification accuracy",
        "proof_points": ["Analytics dashboard", "A/B testing", "Continuous optimization"]
    }
}

# Regional Business Characteristics
BRAZILIAN_REGIONS = {
    "sudeste": {
        "states": ["SP", "RJ", "MG", "ES"],
        "business_style": "fast-paced, direct, results-oriented",
        "decision_speed": "medium to fast",
        "relationship_importance": "medium",
        "preferred_meeting_times": "9-17h, avoid lunch 12-14h"
    },
    "sul": {
        "states": ["RS", "SC", "PR"],
        "business_style": "methodical, relationship-focused, conservative",
        "decision_speed": "slower, more deliberate",
        "relationship_importance": "high",
        "preferred_meeting_times": "avoid mate breaks, respect punctuality"
    },
    "nordeste": {
        "states": ["BA", "PE", "CE", "PB", "RN", "AL", "SE", "MA", "PI"],
        "business_style": "relationship-first, warm, consultative",
        "decision_speed": "relationship-dependent",
        "relationship_importance": "very high",
        "preferred_meeting_times": "flexible, relationship-building focus"
    },
    "centro-oeste": {
        "states": ["GO", "MT", "MS", "DF"],
        "business_style": "growing market, opportunity-focused",
        "decision_speed": "medium",
        "relationship_importance": "medium-high",
        "preferred_meeting_times": "standard business hours"
    },
    "norte": {
        "states": ["AM", "PA", "AC", "RO", "RR", "AP", "TO"],
        "business_style": "emerging market, relationship-important",
        "decision_speed": "varies by location",
        "relationship_importance": "high",
        "preferred_meeting_times": "consider time zones"
    }
}
