"""
NLP Utilities for Nellia Prospector
Advanced text processing, analysis, and Brazilian Portuguese optimization.
"""

import re
import unicodedata
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from collections import Counter
import string
from loguru import logger

@dataclass
class TextAnalysisResult:
    """Result of text analysis operations"""
    cleaned_text: str
    word_count: int
    sentence_count: int
    readability_score: float
    key_phrases: List[str]
    sentiment_indicators: Dict[str, float]
    language_confidence: float
    business_relevance_score: float

@dataclass
class EntityExtractionResult:
    """Result of entity extraction"""
    companies: List[str]
    people: List[str]
    locations: List[str]
    emails: List[str]
    phones: List[str]
    websites: List[str]
    technologies: List[str]
    industries: List[str]

class BrazilianBusinessNLP:
    """NLP utilities optimized for Brazilian business context"""
    
    def __init__(self):
        self.portuguese_stopwords = self._load_portuguese_stopwords()
        self.business_keywords = self._load_business_keywords()
        self.tech_keywords = self._load_tech_keywords()
        self.industry_terms = self._load_industry_terms()
        self.roi_indicators = self._load_roi_indicators()
        
    def _load_portuguese_stopwords(self) -> Set[str]:
        """Load Portuguese stopwords"""
        return {
            'a', 'ao', 'aos', 'aquela', 'aquelas', 'aquele', 'aqueles', 'aquilo',
            'as', 'até', 'com', 'como', 'da', 'das', 'de', 'dela', 'delas', 'dele',
            'deles', 'depois', 'do', 'dos', 'e', 'ela', 'elas', 'ele', 'eles', 'em',
            'entre', 'era', 'eram', 'essa', 'essas', 'esse', 'esses', 'esta',
            'estão', 'estas', 'estava', 'estavam', 'este', 'esteja', 'estejam',
            'estejamos', 'estes', 'esteve', 'estive', 'estivemos', 'estiver',
            'estivera', 'estiveram', 'estiverem', 'estivermos', 'estivesse',
            'estivessem', 'estivéramos', 'estivéssemos', 'estou', 'está', 'estás',
            'estávamos', 'estão', 'eu', 'foi', 'fomos', 'for', 'fora', 'foram',
            'forem', 'formos', 'fosse', 'fossem', 'fui', 'fôramos', 'fôssemos',
            'haja', 'hajam', 'hajamos', 'havemos', 'havia', 'hei', 'houve',
            'houvemos', 'houver', 'houvera', 'houveram', 'houverei', 'houverem',
            'houveremos', 'houveria', 'houveriam', 'houvermos', 'houveríamos',
            'houvesse', 'houvessem', 'houvéramos', 'houvéssemos', 'há', 'hão',
            'isso', 'isto', 'já', 'lhe', 'lhes', 'mais', 'mas', 'me', 'mesmo',
            'meu', 'meus', 'minha', 'minhas', 'muito', 'na', 'nas', 'nem', 'no',
            'nos', 'nossa', 'nossas', 'nosso', 'nossos', 'num', 'numa', 'não',
            'nós', 'o', 'os', 'ou', 'para', 'pela', 'pelas', 'pelo', 'pelos',
            'por', 'qual', 'quando', 'que', 'quem', 'se', 'seja', 'sejam',
            'sejamos', 'sem', 'ser', 'seria', 'seriam', 'será', 'serão', 'seu',
            'seus', 'só', 'são', 'sua', 'suas', 'também', 'te', 'tem', 'temos',
            'tenha', 'tenham', 'tenhamos', 'tenho', 'ter', 'terei', 'teremos',
            'teria', 'teriam', 'terá', 'terão', 'teve', 'tinha', 'tinham',
            'tive', 'tivemos', 'tiver', 'tivera', 'tiveram', 'tiverem',
            'tivermos', 'tivesse', 'tivessem', 'tivéramos', 'tivéssemos',
            'tu', 'tua', 'tuas', 'teu', 'teus', 'um', 'uma', 'você', 'vocês',
            'vos', 'à', 'às', 'éramos', 'é'
        }
    
    def _load_business_keywords(self) -> Set[str]:
        """Load Brazilian business keywords"""
        return {
            'empresa', 'negócio', 'vendas', 'receita', 'lucro', 'faturamento',
            'cliente', 'mercado', 'crescimento', 'expansão', 'investimento',
            'roi', 'retorno', 'produtividade', 'eficiência', 'otimização',
            'automação', 'digitalização', 'transformação', 'inovação',
            'competitividade', 'liderança', 'estratégia', 'resultado',
            'performance', 'melhoria', 'processo', 'qualidade', 'experiência',
            'satisfação', 'engajamento', 'conversão', 'lead', 'prospect',
            'funil', 'pipeline', 'crm', 'gestão', 'administração', 'direção',
            'operação', 'comercial', 'marketing', 'vendedor', 'representante',
            'distribuidor', 'parceiro', 'fornecedor', 'prestador', 'serviço',
            'produto', 'solução', 'tecnologia', 'software', 'sistema',
            'plataforma', 'ferramenta', 'aplicativo', 'dashboard', 'relatório',
            'análise', 'dados', 'informação', 'inteligência', 'artificial',
            'machine', 'learning', 'algoritmo', 'automático', 'digital'
        }
    
    def _load_tech_keywords(self) -> Set[str]:
        """Load technology-related keywords"""
        return {
            'ia', 'ai', 'artificial', 'intelligence', 'machine', 'learning',
            'ml', 'deep', 'neural', 'network', 'algoritmo', 'automation',
            'automação', 'rpa', 'bot', 'chatbot', 'api', 'integration',
            'integração', 'cloud', 'nuvem', 'saas', 'software', 'sistema',
            'plataforma', 'dashboard', 'analytics', 'big', 'data', 'dados',
            'crm', 'erp', 'bi', 'business', 'intelligence', 'digital',
            'digitalização', 'transformação', 'tecnologia', 'tech', 'it',
            'ti', 'desenvolvimento', 'dev', 'programming', 'programação',
            'web', 'mobile', 'app', 'aplicativo', 'database', 'banco',
            'cybersecurity', 'segurança', 'blockchain', 'iot', 'internet',
            'things', 'coisas', 'smart', 'inteligente'
        }
    
    def _load_industry_terms(self) -> Dict[str, Set[str]]:
        """Load industry-specific terms"""
        return {
            'varejo': {'loja', 'varejo', 'retail', 'vendas', 'ponto', 'venda', 'pdv', 'estoque', 'inventário'},
            'financeiro': {'banco', 'financeiro', 'crédito', 'empréstimo', 'investimento', 'seguro', 'fintech'},
            'saúde': {'hospital', 'clínica', 'médico', 'saúde', 'healthcare', 'medicina', 'paciente'},
            'educação': {'escola', 'universidade', 'educação', 'ensino', 'curso', 'treinamento', 'capacitação'},
            'manufatura': {'indústria', 'fábrica', 'produção', 'manufatura', 'industrial', 'fabricação'},
            'logística': {'logística', 'transporte', 'entrega', 'distribuição', 'armazém', 'supply', 'chain'},
            'imobiliário': {'imóvel', 'imobiliário', 'propriedade', 'construção', 'real', 'estate'},
            'agricultura': {'agro', 'agricultura', 'fazenda', 'rural', 'agronegócio', 'plantação'},
            'energia': {'energia', 'elétrica', 'solar', 'eólica', 'petróleo', 'gás', 'utilities'},
            'telecomunicações': {'telecom', 'telecomunicações', 'telefonia', 'internet', 'banda', 'larga'}
        }
    
    def _load_roi_indicators(self) -> Set[str]:
        """Load ROI and value proposition indicators"""
        return {
            'economia', 'economizar', 'redução', 'reduzir', 'corte', 'cortar',
            'otimização', 'otimizar', 'melhoria', 'melhorar', 'eficiência',
            'eficiente', 'produtividade', 'produtivo', 'aumento', 'aumentar',
            'crescimento', 'crescer', 'lucro', 'lucrativo', 'receita',
            'faturamento', 'retorno', 'roi', 'investimento', 'benefício',
            'vantagem', 'competitivo', 'diferencial', 'valor', 'resultado',
            'performance', 'desempenho', 'ganho', 'ganhar', 'save', 'saving',
            'cost', 'custo', 'tempo', 'rapidez', 'rápido', 'agilidade',
            'ágil', 'automatização', 'automático', 'escalabilidade',
            'escalável', 'sustentabilidade', 'sustentável'
        }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text for processing"""
        if not text:
            return ""
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep Portuguese accents
        text = re.sub(r'[^\w\s\-\.@áàâãéèêíìîóòôõúùûç]', ' ', text, flags=re.UNICODE)
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def extract_entities(self, text: str) -> EntityExtractionResult:
        """Extract business entities from text"""
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text, re.IGNORECASE)
        
        # Phone patterns (Brazilian format)
        phone_patterns = [
            r'\(\d{2}\)\s*\d{4,5}-?\d{4}',  # (11) 99999-9999
            r'\d{2}\s*\d{4,5}-?\d{4}',      # 11 99999-9999
            r'\+55\s*\d{2}\s*\d{4,5}-?\d{4}' # +55 11 99999-9999
        ]
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text))
        
        # Website patterns
        website_pattern = r'(?:https?://)?(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?'
        websites = re.findall(website_pattern, text, re.IGNORECASE)
        
        # Company indicators (simple heuristic)
        company_indicators = ['ltda', 'ltd', 's.a.', 'sa', 'me', 'epp', 'eireli', 'corp', 'inc']
        company_pattern = r'\b[A-ZÀÁÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛ][a-zA-ZÀ-ÿ\s&-]+(?:' + '|'.join(company_indicators) + r')\b'
        companies = re.findall(company_pattern, text, re.IGNORECASE)
        
        # People names (simple heuristic for Brazilian names)
        name_pattern = r'\b[A-ZÀÁÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛ][a-zàáâãéèêíìîóòôõúùû]+(?:\s+[A-ZÀÁÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛ][a-zàáâãéèêíìîóòôõúùû]+)+\b'
        people = re.findall(name_pattern, text)
        
        # Brazilian locations
        location_indicators = ['são paulo', 'rio de janeiro', 'belo horizonte', 'brasília', 'salvador', 
                              'fortaleza', 'curitiba', 'recife', 'porto alegre', 'goiânia']
        locations = []
        for indicator in location_indicators:
            if indicator.lower() in text.lower():
                locations.append(indicator.title())
        
        # Technology terms
        technologies = [term for term in self.tech_keywords if term.lower() in text.lower()]
        
        # Industry classification
        industries = []
        for industry, terms in self.industry_terms.items():
            if any(term.lower() in text.lower() for term in terms):
                industries.append(industry)
        
        return EntityExtractionResult(
            companies=list(set(companies)),
            people=list(set(people)),
            locations=list(set(locations)),
            emails=list(set(emails)),
            phones=list(set(phones)),
            websites=list(set(websites)),
            technologies=list(set(technologies)),
            industries=list(set(industries))
        )
    
    def calculate_business_relevance(self, text: str) -> float:
        """Calculate business relevance score for text"""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        words = self._tokenize(text_lower)
        
        # Count business keywords
        business_score = sum(1 for word in words if word in self.business_keywords)
        tech_score = sum(1 for word in words if word in self.tech_keywords)
        roi_score = sum(1 for word in words if word in self.roi_indicators)
        
        # Calculate relative scores
        total_words = len(words)
        if total_words == 0:
            return 0.0
        
        business_ratio = business_score / total_words
        tech_ratio = tech_score / total_words
        roi_ratio = roi_score / total_words
        
        # Weighted combination
        relevance_score = (business_ratio * 0.4 + tech_ratio * 0.3 + roi_ratio * 0.3)
        
        # Normalize to 0-1 scale
        return min(relevance_score * 10, 1.0)
    
    def calculate_readability_score(self, text: str) -> float:
        """Calculate readability score (simplified for Portuguese)"""
        if not text:
            return 0.0
        
        sentences = self._split_sentences(text)
        words = self._tokenize(text.lower())
        
        if len(sentences) == 0 or len(words) == 0:
            return 0.0
        
        # Average words per sentence
        avg_words_per_sentence = len(words) / len(sentences)
        
        # Average syllables per word (simplified)
        vowels = 'aeiouáàâãéèêíìîóòôõúùû'
        syllable_count = sum(1 for word in words for char in word if char in vowels)
        avg_syllables_per_word = syllable_count / len(words) if len(words) > 0 else 0
        
        # Simplified readability formula
        readability = 206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
        
        # Normalize to 0-1 scale
        return max(0, min(readability / 100, 1.0))
    
    def extract_key_phrases(self, text: str, max_phrases: int = 10) -> List[str]:
        """Extract key phrases from text"""
        if not text:
            return []
        
        # Simple n-gram extraction
        words = self._tokenize(text.lower())
        filtered_words = [word for word in words if word not in self.portuguese_stopwords and len(word) > 2]
        
        phrases = []
        
        # Extract 2-grams and 3-grams
        for i in range(len(filtered_words) - 1):
            bigram = f"{filtered_words[i]} {filtered_words[i+1]}"
            phrases.append(bigram)
            
            if i < len(filtered_words) - 2:
                trigram = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
                phrases.append(trigram)
        
        # Count phrase frequency
        phrase_counts = Counter(phrases)
        
        # Return most common phrases
        return [phrase for phrase, count in phrase_counts.most_common(max_phrases)]
    
    def analyze_sentiment_indicators(self, text: str) -> Dict[str, float]:
        """Analyze sentiment indicators in text"""
        if not text:
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
        
        positive_words = {
            'bom', 'boa', 'excelente', 'ótimo', 'ótima', 'fantástico', 'maravilhoso',
            'perfeito', 'sucesso', 'vantagem', 'benefício', 'melhoria', 'crescimento',
            'inovação', 'eficiente', 'produtivo', 'lucrativo', 'positivo', 'satisfeito',
            'feliz', 'contente', 'animado', 'confiante', 'seguro', 'forte', 'líder',
            'melhor', 'superior', 'avançado', 'moderno', 'novo', 'revolucionário'
        }
        
        negative_words = {
            'ruim', 'péssimo', 'péssima', 'terrível', 'horrível', 'problema', 'dificuldade',
            'desafio', 'obstáculo', 'falha', 'erro', 'perda', 'prejuízo', 'redução',
            'queda', 'declínio', 'crise', 'dor', 'frustração', 'insatisfação',
            'preocupação', 'medo', 'receio', 'negativo', 'fraco', 'inferior',
            'atrasado', 'obsoleto', 'antigo', 'lento', 'ineficiente'
        }
        
        words = self._tokenize(text.lower())
        
        positive_count = sum(1 for word in words if word in positive_words)
        negative_count = sum(1 for word in words if word in negative_words)
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return {"positive": 0.0, "negative": 0.0, "neutral": 1.0}
        
        positive_score = positive_count / total_sentiment_words
        negative_score = negative_count / total_sentiment_words
        neutral_score = 1.0 - positive_score - negative_score
        
        return {
            "positive": positive_score,
            "negative": negative_score,
            "neutral": max(0.0, neutral_score)
        }
    
    def detect_language_confidence(self, text: str) -> float:
        """Detect if text is Portuguese with confidence score"""
        if not text:
            return 0.0
        
        portuguese_indicators = {
            'ção', 'ões', 'ão', 'são', 'não', 'com', 'para', 'que', 'uma', 'dos',
            'das', 'nos', 'nas', 'pela', 'pelo', 'pelos', 'pelas', 'também',
            'já', 'mais', 'muito', 'quando', 'como', 'onde', 'porque', 'através'
        }
        
        words = self._tokenize(text.lower())
        portuguese_matches = sum(1 for word in words if any(indicator in word for indicator in portuguese_indicators))
        
        if len(words) == 0:
            return 0.0
        
        confidence = min(portuguese_matches / len(words) * 3, 1.0)
        return confidence
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        # Remove punctuation and split
        translator = str.maketrans('', '', string.punctuation)
        text = text.translate(translator)
        return [word for word in text.split() if len(word) > 0]
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentence_endings = r'[.!?]+\s+'
        sentences = re.split(sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def analyze_text(self, text: str) -> TextAnalysisResult:
        """Comprehensive text analysis"""
        if not text:
            return TextAnalysisResult(
                cleaned_text="",
                word_count=0,
                sentence_count=0,
                readability_score=0.0,
                key_phrases=[],
                sentiment_indicators={"positive": 0.0, "negative": 0.0, "neutral": 1.0},
                language_confidence=0.0,
                business_relevance_score=0.0
            )
        
        cleaned_text = self.clean_text(text)
        words = self._tokenize(cleaned_text.lower())
        sentences = self._split_sentences(cleaned_text)
        
        return TextAnalysisResult(
            cleaned_text=cleaned_text,
            word_count=len(words),
            sentence_count=len(sentences),
            readability_score=self.calculate_readability_score(cleaned_text),
            key_phrases=self.extract_key_phrases(cleaned_text),
            sentiment_indicators=self.analyze_sentiment_indicators(cleaned_text),
            language_confidence=self.detect_language_confidence(cleaned_text),
            business_relevance_score=self.calculate_business_relevance(cleaned_text)
        )


# Global NLP instance
_nlp_instance: Optional[BrazilianBusinessNLP] = None

def get_nlp() -> BrazilianBusinessNLP:
    """Get the global NLP instance"""
    global _nlp_instance
    if _nlp_instance is None:
        _nlp_instance = BrazilianBusinessNLP()
    return _nlp_instance

def clean_text(text: str) -> str:
    """Clean text using global NLP instance"""
    return get_nlp().clean_text(text)

def extract_entities(text: str) -> EntityExtractionResult:
    """Extract entities using global NLP instance"""
    return get_nlp().extract_entities(text)

def calculate_business_relevance(text: str) -> float:
    """Calculate business relevance using global NLP instance"""
    return get_nlp().calculate_business_relevance(text)

def analyze_text(text: str) -> TextAnalysisResult:
    """Analyze text using global NLP instance"""
    return get_nlp().analyze_text(text)
