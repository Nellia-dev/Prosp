"""
Unit tests for data models and lead structures
"""

import pytest
from datetime import datetime
from typing import Dict, Any
from data_models.lead_structures import (
    Lead, ContactInfo, CompanyInfo, LeadAnalysisResult, PersonaProfile,
    ApproachStrategy, MessageContent, ProcessingResult, EnhancedLeadData,
    ValidationError, create_lead_from_dict, validate_lead_data
)

class TestContactInfo:
    """Test ContactInfo data class"""
    
    def test_contact_info_creation(self):
        """Test basic ContactInfo creation"""
        contact = ContactInfo(
            name="João Silva",
            title="CEO",
            email="joao@empresa.com",
            phone="(11) 99999-9999",
            linkedin="linkedin.com/in/joaosilva"
        )
        assert contact.name == "João Silva"
        assert contact.title == "CEO"
        assert contact.email == "joao@empresa.com"
        assert contact.phone == "(11) 99999-9999"
        assert contact.linkedin == "linkedin.com/in/joaosilva"
    
    def test_contact_info_optional_fields(self):
        """Test ContactInfo with optional fields"""
        contact = ContactInfo(name="Maria Santos")
        assert contact.name == "Maria Santos"
        assert contact.title is None
        assert contact.email is None
        assert contact.phone is None
        assert contact.linkedin is None
    
    def test_contact_info_to_dict(self):
        """Test ContactInfo serialization"""
        contact = ContactInfo(
            name="João Silva",
            title="CEO",
            email="joao@empresa.com"
        )
        contact_dict = contact.to_dict()
        
        assert isinstance(contact_dict, dict)
        assert contact_dict["name"] == "João Silva"
        assert contact_dict["title"] == "CEO"
        assert contact_dict["email"] == "joao@empresa.com"
        assert "phone" in contact_dict
        assert "linkedin" in contact_dict
    
    def test_contact_info_from_dict(self):
        """Test ContactInfo deserialization"""
        contact_dict = {
            "name": "Ana Costa",
            "title": "CTO",
            "email": "ana@tech.com",
            "phone": "+55 11 98888-8888",
            "linkedin": "linkedin.com/in/anacosta"
        }
        contact = ContactInfo.from_dict(contact_dict)
        
        assert contact.name == "Ana Costa"
        assert contact.title == "CTO"
        assert contact.email == "ana@tech.com"
        assert contact.phone == "+55 11 98888-8888"
        assert contact.linkedin == "linkedin.com/in/anacosta"


class TestCompanyInfo:
    """Test CompanyInfo data class"""
    
    def test_company_info_creation(self):
        """Test basic CompanyInfo creation"""
        company = CompanyInfo(
            name="TechCorp Brasil",
            industry="Tecnologia",
            size="100-500",
            location="São Paulo, SP",
            website="www.techcorp.com.br",
            description="Empresa de soluções tecnológicas"
        )
        assert company.name == "TechCorp Brasil"
        assert company.industry == "Tecnologia"
        assert company.size == "100-500"
        assert company.location == "São Paulo, SP"
        assert company.website == "www.techcorp.com.br"
        assert company.description == "Empresa de soluções tecnológicas"
    
    def test_company_info_to_dict(self):
        """Test CompanyInfo serialization"""
        company = CompanyInfo(
            name="InnovaCorp",
            industry="Inovação"
        )
        company_dict = company.to_dict()
        
        assert isinstance(company_dict, dict)
        assert company_dict["name"] == "InnovaCorp"
        assert company_dict["industry"] == "Inovação"
        assert "size" in company_dict
        assert "location" in company_dict
    
    def test_company_info_from_dict(self):
        """Test CompanyInfo deserialization"""
        company_dict = {
            "name": "SalesForce Brasil",
            "industry": "Software",
            "size": "1000+",
            "location": "Rio de Janeiro, RJ",
            "website": "salesforce.com.br",
            "description": "Plataforma de CRM"
        }
        company = CompanyInfo.from_dict(company_dict)
        
        assert company.name == "SalesForce Brasil"
        assert company.industry == "Software"
        assert company.size == "1000+"
        assert company.location == "Rio de Janeiro, RJ"
        assert company.website == "salesforce.com.br"
        assert company.description == "Plataforma de CRM"


class TestLead:
    """Test Lead data class"""
    
    def test_lead_creation_minimal(self):
        """Test Lead creation with minimal data"""
        lead = Lead(
            source_text="João Silva, CEO da TechCorp, busca soluções de automação",
            source="website"
        )
        assert lead.source_text == "João Silva, CEO da TechCorp, busca soluções de automação"
        assert lead.source == "website"
        assert lead.contact_info is None
        assert lead.company_info is None
        assert isinstance(lead.created_at, datetime)
        assert lead.lead_id is not None
        assert len(lead.lead_id) > 0
    
    def test_lead_creation_complete(self):
        """Test Lead creation with complete data"""
        contact = ContactInfo(name="João Silva", title="CEO")
        company = CompanyInfo(name="TechCorp", industry="Tecnologia")
        
        lead = Lead(
            source_text="Texto original do lead",
            source="linkedin",
            contact_info=contact,
            company_info=company
        )
        
        assert lead.contact_info == contact
        assert lead.company_info == company
        assert lead.source == "linkedin"
    
    def test_lead_to_dict(self):
        """Test Lead serialization"""
        contact = ContactInfo(name="Maria Santos", email="maria@empresa.com")
        company = CompanyInfo(name="EmpresaCorp", industry="Varejo")
        
        lead = Lead(
            source_text="Lead text",
            source="email",
            contact_info=contact,
            company_info=company
        )
        
        lead_dict = lead.to_dict()
        
        assert isinstance(lead_dict, dict)
        assert lead_dict["source_text"] == "Lead text"
        assert lead_dict["source"] == "email"
        assert "contact_info" in lead_dict
        assert "company_info" in lead_dict
        assert "created_at" in lead_dict
        assert "lead_id" in lead_dict
        
        # Check nested objects
        assert lead_dict["contact_info"]["name"] == "Maria Santos"
        assert lead_dict["company_info"]["name"] == "EmpresaCorp"
    
    def test_lead_from_dict(self):
        """Test Lead deserialization"""
        lead_dict = {
            "source_text": "Texto do lead de teste",
            "source": "manual",
            "contact_info": {
                "name": "Carlos Oliveira",
                "title": "Diretor",
                "email": "carlos@oliveira.com"
            },
            "company_info": {
                "name": "Oliveira & Associados",
                "industry": "Consultoria",
                "size": "50-100"
            },
            "lead_id": "test-123",
            "created_at": "2024-01-01T12:00:00"
        }
        
        lead = Lead.from_dict(lead_dict)
        
        assert lead.source_text == "Texto do lead de teste"
        assert lead.source == "manual"
        assert lead.contact_info.name == "Carlos Oliveira"
        assert lead.company_info.name == "Oliveira & Associados"
        assert lead.lead_id == "test-123"


class TestLeadAnalysisResult:
    """Test LeadAnalysisResult data class"""
    
    def test_analysis_result_creation(self):
        """Test LeadAnalysisResult creation"""
        result = LeadAnalysisResult(
            relevance_score=0.85,
            qualification_score=0.75,
            pain_points=["Automação de processos", "Redução de custos"],
            business_potential="Alto",
            industry_fit=True,
            confidence_score=0.90
        )
        
        assert result.relevance_score == 0.85
        assert result.qualification_score == 0.75
        assert len(result.pain_points) == 2
        assert "Automação de processos" in result.pain_points
        assert result.business_potential == "Alto"
        assert result.industry_fit is True
        assert result.confidence_score == 0.90
    
    def test_analysis_result_to_dict(self):
        """Test LeadAnalysisResult serialization"""
        result = LeadAnalysisResult(
            relevance_score=0.80,
            qualification_score=0.70,
            pain_points=["Vendas", "Marketing"],
            business_potential="Médio"
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["relevance_score"] == 0.80
        assert result_dict["qualification_score"] == 0.70
        assert result_dict["pain_points"] == ["Vendas", "Marketing"]
        assert result_dict["business_potential"] == "Médio"


class TestPersonaProfile:
    """Test PersonaProfile data class"""
    
    def test_persona_profile_creation(self):
        """Test PersonaProfile creation"""
        profile = PersonaProfile(
            role_level="C-Level",
            decision_maker=True,
            likely_pain_points=["Eficiência operacional", "ROI"],
            communication_style="Direto e objetivo",
            preferred_approach="Dados e resultados",
            risk_tolerance="Conservador"
        )
        
        assert profile.role_level == "C-Level"
        assert profile.decision_maker is True
        assert len(profile.likely_pain_points) == 2
        assert profile.communication_style == "Direto e objetivo"
        assert profile.preferred_approach == "Dados e resultados"
        assert profile.risk_tolerance == "Conservador"
    
    def test_persona_profile_to_dict(self):
        """Test PersonaProfile serialization"""
        profile = PersonaProfile(
            role_level="Gerência",
            decision_maker=False,
            likely_pain_points=["Produtividade"]
        )
        
        profile_dict = profile.to_dict()
        
        assert isinstance(profile_dict, dict)
        assert profile_dict["role_level"] == "Gerência"
        assert profile_dict["decision_maker"] is False
        assert profile_dict["likely_pain_points"] == ["Produtividade"]


class TestApproachStrategy:
    """Test ApproachStrategy data class"""
    
    def test_approach_strategy_creation(self):
        """Test ApproachStrategy creation"""
        strategy = ApproachStrategy(
            primary_angle="ROI e eficiência",
            key_value_props=["Redução de 30% nos custos", "Aumento de 50% na produtividade"],
            objection_handling={"preço": "ROI comprovado em 6 meses"},
            recommended_channel="LinkedIn",
            timing_suggestion="Segunda-feira, manhã",
            follow_up_strategy="Sequência de 3 touchpoints"
        )
        
        assert strategy.primary_angle == "ROI e eficiência"
        assert len(strategy.key_value_props) == 2
        assert "preço" in strategy.objection_handling
        assert strategy.recommended_channel == "LinkedIn"
        assert strategy.timing_suggestion == "Segunda-feira, manhã"
        assert strategy.follow_up_strategy == "Sequência de 3 touchpoints"


class TestMessageContent:
    """Test MessageContent data class"""
    
    def test_message_content_creation(self):
        """Test MessageContent creation"""
        message = MessageContent(
            subject="Proposta de automação para TechCorp",
            opening="Olá João,",
            body="Identificamos uma oportunidade...",
            call_to_action="Podemos agendar uma conversa?",
            closing="Atenciosamente,",
            channel="email",
            tone="profissional"
        )
        
        assert message.subject == "Proposta de automação para TechCorp"
        assert message.opening == "Olá João,"
        assert message.body == "Identificamos uma oportunidade..."
        assert message.call_to_action == "Podemos agendar uma conversa?"
        assert message.closing == "Atenciosamente,"
        assert message.channel == "email"
        assert message.tone == "profissional"
    
    def test_message_content_to_dict(self):
        """Test MessageContent serialization"""
        message = MessageContent(
            subject="Teste",
            body="Corpo da mensagem",
            channel="linkedin"
        )
        
        message_dict = message.to_dict()
        
        assert isinstance(message_dict, dict)
        assert message_dict["subject"] == "Teste"
        assert message_dict["body"] == "Corpo da mensagem"
        assert message_dict["channel"] == "linkedin"


class TestProcessingResult:
    """Test ProcessingResult data class"""
    
    def test_processing_result_creation(self):
        """Test ProcessingResult creation"""
        lead = Lead(source_text="Test lead", source="test")
        analysis = LeadAnalysisResult(
            relevance_score=0.8,
            qualification_score=0.7,
            pain_points=["test"],
            business_potential="Alto"
        )
        persona = PersonaProfile(
            role_level="Manager",
            decision_maker=True,
            likely_pain_points=["efficiency"]
        )
        strategy = ApproachStrategy(
            primary_angle="efficiency",
            key_value_props=["save time"],
            objection_handling={},
            recommended_channel="email"
        )
        message = MessageContent(
            subject="Test",
            body="Test message",
            channel="email"
        )
        
        result = ProcessingResult(
            original_lead=lead,
            analysis=analysis,
            persona=persona,
            strategy=strategy,
            message=message,
            processing_status="completed",
            processing_time=1.5
        )
        
        assert result.original_lead == lead
        assert result.analysis == analysis
        assert result.persona == persona
        assert result.strategy == strategy
        assert result.message == message
        assert result.processing_status == "completed"
        assert result.processing_time == 1.5
        assert isinstance(result.processed_at, datetime)
    
    def test_processing_result_to_dict(self):
        """Test ProcessingResult serialization"""
        lead = Lead(source_text="Test", source="test")
        analysis = LeadAnalysisResult(
            relevance_score=0.8,
            qualification_score=0.7,
            pain_points=["test"],
            business_potential="Alto"
        )
        
        result = ProcessingResult(
            original_lead=lead,
            analysis=analysis,
            processing_status="completed"
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert "original_lead" in result_dict
        assert "analysis" in result_dict
        assert "processing_status" in result_dict
        assert "processed_at" in result_dict


class TestEnhancedLeadData:
    """Test EnhancedLeadData data class"""
    
    def test_enhanced_lead_data_creation(self):
        """Test EnhancedLeadData creation"""
        enhanced = EnhancedLeadData(
            company_research="Pesquisa detalhada sobre a empresa",
            recent_news=["Empresa expandiu operações", "Novo CEO contratado"],
            technology_stack=["Salesforce", "HubSpot", "Python"],
            competitors=["Competitor A", "Competitor B"],
            financial_indicators={"revenue": "R$ 10M", "growth": "15%"},
            social_proof=["Case study XYZ", "Cliente satisfeito ABC"]
        )
        
        assert enhanced.company_research == "Pesquisa detalhada sobre a empresa"
        assert len(enhanced.recent_news) == 2
        assert len(enhanced.technology_stack) == 3
        assert len(enhanced.competitors) == 2
        assert enhanced.financial_indicators["revenue"] == "R$ 10M"
        assert len(enhanced.social_proof) == 2


class TestValidationAndUtilities:
    """Test validation functions and utilities"""
    
    def test_validate_lead_data_valid(self):
        """Test validation with valid lead data"""
        lead_data = {
            "source_text": "João Silva, CEO da TechCorp",
            "source": "linkedin",
            "contact_info": {
                "name": "João Silva",
                "email": "joao@techcorp.com"
            },
            "company_info": {
                "name": "TechCorp",
                "industry": "Tecnologia"
            }
        }
        
        # Should not raise any exception
        validate_lead_data(lead_data)
    
    def test_validate_lead_data_missing_required(self):
        """Test validation with missing required fields"""
        lead_data = {
            "source": "linkedin"
            # Missing source_text
        }
        
        with pytest.raises(ValidationError):
            validate_lead_data(lead_data)
    
    def test_validate_lead_data_invalid_email(self):
        """Test validation with invalid email"""
        lead_data = {
            "source_text": "Test lead",
            "source": "test",
            "contact_info": {
                "name": "Test User",
                "email": "invalid-email"
            }
        }
        
        with pytest.raises(ValidationError):
            validate_lead_data(lead_data)
    
    def test_create_lead_from_dict_valid(self):
        """Test lead creation from valid dictionary"""
        lead_data = {
            "source_text": "Maria Santos, diretora de vendas",
            "source": "website",
            "contact_info": {
                "name": "Maria Santos",
                "title": "Diretora de Vendas",
                "email": "maria@empresa.com"
            }
        }
        
        lead = create_lead_from_dict(lead_data)
        
        assert isinstance(lead, Lead)
        assert lead.source_text == "Maria Santos, diretora de vendas"
        assert lead.source == "website"
        assert lead.contact_info.name == "Maria Santos"
        assert lead.contact_info.title == "Diretora de Vendas"
        assert lead.contact_info.email == "maria@empresa.com"
    
    def test_create_lead_from_dict_invalid(self):
        """Test lead creation from invalid dictionary"""
        invalid_data = {
            "source": "test"
            # Missing required source_text
        }
        
        with pytest.raises(ValidationError):
            create_lead_from_dict(invalid_data)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_lead_with_empty_strings(self):
        """Test lead creation with empty strings"""
        lead = Lead(source_text="", source="test")
        assert lead.source_text == ""
        assert lead.source == "test"
    
    def test_contact_info_with_long_name(self):
        """Test contact info with very long name"""
        long_name = "João " * 100  # Very long name
        contact = ContactInfo(name=long_name)
        assert contact.name == long_name
    
    def test_serialization_with_none_values(self):
        """Test serialization handles None values correctly"""
        contact = ContactInfo(name="Test")
        contact_dict = contact.to_dict()
        
        # Should include None values
        assert contact_dict["title"] is None
        assert contact_dict["email"] is None
        assert contact_dict["phone"] is None
        assert contact_dict["linkedin"] is None
    
    def test_deserialization_missing_optional_fields(self):
        """Test deserialization with missing optional fields"""
        contact_data = {"name": "Test User"}
        contact = ContactInfo.from_dict(contact_data)
        
        assert contact.name == "Test User"
        assert contact.title is None
        assert contact.email is None


if __name__ == "__main__":
    pytest.main([__file__])