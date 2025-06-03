"""
Unit tests for file handler utilities
"""

import pytest
import json
import csv
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open
from utils.file_handler import (
    FileHandler, read_json_file, write_json_file, read_csv_file, write_csv_file,
    read_text_file, write_text_file, ensure_directory, get_file_extension,
    is_valid_file_path, backup_file, FileHandlerError
)
from data_models.lead_structures import Lead, ContactInfo, CompanyInfo

class TestFileHandler:
    """Test FileHandler class"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.handler = FileHandler()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        # Clean up temp directory
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)
    
    def test_initialization(self):
        """Test FileHandler initialization"""
        handler = FileHandler()
        assert handler.supported_formats == ['.json', '.csv', '.txt', '.md']
        assert handler.encoding == 'utf-8'
    
    def test_custom_initialization(self):
        """Test FileHandler with custom parameters"""
        handler = FileHandler(
            supported_formats=['.json', '.xml'],
            encoding='latin-1',
            backup_enabled=False
        )
        assert handler.supported_formats == ['.json', '.xml']
        assert handler.encoding == 'latin-1'
        assert handler.backup_enabled is False


class TestJSONOperations:
    """Test JSON file operations"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)
    
    def test_write_and_read_json(self):
        """Test writing and reading JSON files"""
        test_data = {
            "name": "João Silva",
            "company": "TechCorp",
            "email": "joao@techcorp.com",
            "tags": ["CEO", "Technology", "São Paulo"]
        }
        
        json_file = self.temp_path / "test.json"
        
        # Write JSON
        write_json_file(str(json_file), test_data)
        assert json_file.exists()
        
        # Read JSON
        read_data = read_json_file(str(json_file))
        assert read_data == test_data
    
    def test_write_json_with_unicode(self):
        """Test JSON handling with Unicode characters"""
        unicode_data = {
            "empresa": "Soluções Tecnológicas Ltda",
            "descrição": "Automação e otimização de processos",
            "localização": "São Paulo, Brasil",
            "especialidades": ["IA", "Machine Learning", "Análise de Dados"]
        }
        
        json_file = self.temp_path / "unicode_test.json"
        
        write_json_file(str(json_file), unicode_data)
        read_data = read_json_file(str(json_file))
        
        assert read_data == unicode_data
        assert read_data["empresa"] == "Soluções Tecnológicas Ltda"
    
    def test_read_nonexistent_json(self):
        """Test reading non-existent JSON file"""
        nonexistent_file = self.temp_path / "nonexistent.json"
        
        with pytest.raises(FileHandlerError):
            read_json_file(str(nonexistent_file))
    
    def test_write_json_invalid_path(self):
        """Test writing JSON to invalid path"""
        invalid_path = "/invalid/path/test.json"
        
        with pytest.raises(FileHandlerError):
            write_json_file(invalid_path, {"test": "data"})
    
    def test_read_invalid_json(self):
        """Test reading invalid JSON content"""
        invalid_json_file = self.temp_path / "invalid.json"
        
        # Write invalid JSON
        with open(invalid_json_file, 'w', encoding='utf-8') as f:
            f.write("{ invalid json content")
        
        with pytest.raises(FileHandlerError):
            read_json_file(str(invalid_json_file))


class TestCSVOperations:
    """Test CSV file operations"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)
    
    def test_write_and_read_csv_with_headers(self):
        """Test writing and reading CSV with headers"""
        test_data = [
            {"name": "João Silva", "company": "TechCorp", "email": "joao@techcorp.com"},
            {"name": "Maria Santos", "company": "InnovaCorp", "email": "maria@innovacorp.com"},
            {"name": "Carlos Oliveira", "company": "DataTech", "email": "carlos@datatech.com"}
        ]
        
        csv_file = self.temp_path / "test.csv"
        
        # Write CSV
        write_csv_file(str(csv_file), test_data, headers=["name", "company", "email"])
        assert csv_file.exists()
        
        # Read CSV
        read_data = read_csv_file(str(csv_file), has_headers=True)
        assert len(read_data) == 3
        assert read_data[0]["name"] == "João Silva"
        assert read_data[1]["company"] == "InnovaCorp"
    
    def test_write_and_read_csv_without_headers(self):
        """Test writing and reading CSV without headers"""
        test_data = [
            ["João Silva", "TechCorp", "joao@techcorp.com"],
            ["Maria Santos", "InnovaCorp", "maria@innovacorp.com"]
        ]
        
        csv_file = self.temp_path / "no_headers.csv"
        
        # Write CSV
        write_csv_file(str(csv_file), test_data)
        assert csv_file.exists()
        
        # Read CSV
        read_data = read_csv_file(str(csv_file), has_headers=False)
        assert len(read_data) == 2
        assert read_data[0] == ["João Silva", "TechCorp", "joao@techcorp.com"]
    
    def test_csv_with_unicode_and_special_chars(self):
        """Test CSV with Unicode and special characters"""
        test_data = [
            {"nome": "João da Silva & Associados", "descrição": "Consultoria em TI, IA e automação"},
            {"nome": "Maria José Ltda.", "descrição": "Soluções para o agronegócio brasileiro"}
        ]
        
        csv_file = self.temp_path / "unicode.csv"
        
        write_csv_file(str(csv_file), test_data, headers=["nome", "descrição"])
        read_data = read_csv_file(str(csv_file), has_headers=True)
        
        assert len(read_data) == 2
        assert "João da Silva & Associados" in read_data[0]["nome"]
        assert "agronegócio" in read_data[1]["descrição"]
    
    def test_read_nonexistent_csv(self):
        """Test reading non-existent CSV file"""
        nonexistent_file = self.temp_path / "nonexistent.csv"
        
        with pytest.raises(FileHandlerError):
            read_csv_file(str(nonexistent_file))
    
    def test_empty_csv_handling(self):
        """Test handling of empty CSV files"""
        empty_csv = self.temp_path / "empty.csv"
        
        # Create empty file
        empty_csv.touch()
        
        read_data = read_csv_file(str(empty_csv))
        assert read_data == []


class TestTextOperations:
    """Test text file operations"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)
    
    def test_write_and_read_text(self):
        """Test writing and reading text files"""
        test_text = """Este é um arquivo de texto de teste.
        Contém múltiplas linhas.
        E caracteres especiais: ção, ã, ñ, €.
        
        Também inclui linhas em branco."""
        
        text_file = self.temp_path / "test.txt"
        
        # Write text
        write_text_file(str(text_file), test_text)
        assert text_file.exists()
        
        # Read text
        read_text = read_text_file(str(text_file))
        assert read_text.strip() == test_text.strip()
    
    def test_write_text_with_encoding(self):
        """Test writing text with specific encoding"""
        portuguese_text = "Soluções de automação para empresas brasileiras"
        text_file = self.temp_path / "portuguese.txt"
        
        write_text_file(str(text_file), portuguese_text, encoding='utf-8')
        read_text = read_text_file(str(text_file), encoding='utf-8')
        
        assert read_text.strip() == portuguese_text
    
    def test_read_nonexistent_text_file(self):
        """Test reading non-existent text file"""
        nonexistent_file = self.temp_path / "nonexistent.txt"
        
        with pytest.raises(FileHandlerError):
            read_text_file(str(nonexistent_file))
    
    def test_large_text_file(self):
        """Test handling large text files"""
        large_text = "Esta é uma linha de teste.\n" * 10000
        text_file = self.temp_path / "large.txt"
        
        write_text_file(str(text_file), large_text)
        read_text = read_text_file(str(text_file))
        
        assert len(read_text.split('\n')) >= 10000


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_get_file_extension(self):
        """Test file extension detection"""
        test_cases = [
            ("file.json", ".json"),
            ("data.csv", ".csv"),
            ("document.txt", ".txt"),
            ("readme.md", ".md"),
            ("file.JSON", ".json"),  # Case insensitive
            ("file", ""),
            ("file.", ""),
            ("/path/to/file.json", ".json"),
            ("file.tar.gz", ".gz")
        ]
        
        for filename, expected in test_cases:
            assert get_file_extension(filename) == expected
    
    def test_is_valid_file_path(self):
        """Test file path validation"""
        valid_paths = [
            "/valid/path/file.json",
            "relative/path/file.csv",
            "file.txt",
            "./local/file.json",
            "../parent/file.csv"
        ]
        
        invalid_paths = [
            "",
            None,
            "/invalid\x00path/file.json",  # Null character
            "file|invalid.json",           # Invalid character
            "con.json",                    # Reserved name on Windows
        ]
        
        for path in valid_paths:
            assert is_valid_file_path(path), f"Path should be valid: {path}"
        
        for path in invalid_paths:
            assert not is_valid_file_path(path), f"Path should be invalid: {path}"
    
    def test_ensure_directory(self):
        """Test directory creation"""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        try:
            # Test creating nested directory
            new_dir = temp_path / "nested" / "directory" / "structure"
            ensure_directory(str(new_dir))
            assert new_dir.exists()
            assert new_dir.is_dir()
            
            # Test with existing directory
            ensure_directory(str(new_dir))  # Should not raise error
            assert new_dir.exists()
            
        finally:
            import shutil
            shutil.rmtree(temp_path)
    
    def test_backup_file(self):
        """Test file backup functionality"""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        try:
            # Create original file
            original_file = temp_path / "original.json"
            test_data = {"test": "data", "timestamp": "2024-01-01"}
            
            with open(original_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f)
            
            # Create backup
            backup_path = backup_file(str(original_file))
            
            assert Path(backup_path).exists()
            assert "backup" in backup_path or ".bak" in backup_path
            
            # Verify backup content
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            assert backup_data == test_data
            
        finally:
            import shutil
            shutil.rmtree(temp_path)


class TestLeadDataProcessing:
    """Test file operations with lead data structures"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)
    
    def test_export_leads_to_json(self):
        """Test exporting leads to JSON format"""
        # Create sample leads
        leads = [
            Lead(
                source_text="João Silva, CEO da TechCorp",
                source="linkedin",
                contact_info=ContactInfo(
                    name="João Silva",
                    title="CEO",
                    email="joao@techcorp.com"
                ),
                company_info=CompanyInfo(
                    name="TechCorp",
                    industry="Tecnologia"
                )
            ),
            Lead(
                source_text="Maria Santos, Diretora de Vendas",
                source="website",
                contact_info=ContactInfo(
                    name="Maria Santos",
                    title="Diretora de Vendas",
                    email="maria@empresa.com"
                )
            )
        ]
        
        # Convert to dictionaries
        leads_data = [lead.to_dict() for lead in leads]
        
        # Export to JSON
        json_file = self.temp_path / "leads_export.json"
        write_json_file(str(json_file), leads_data)
        
        # Read back and verify
        imported_data = read_json_file(str(json_file))
        assert len(imported_data) == 2
        assert imported_data[0]["contact_info"]["name"] == "João Silva"
        assert imported_data[1]["source"] == "website"
    
    def test_export_leads_to_csv(self):
        """Test exporting leads to CSV format"""
        # Create sample leads data for CSV
        leads_csv_data = [
            {
                "name": "João Silva",
                "title": "CEO", 
                "company": "TechCorp",
                "email": "joao@techcorp.com",
                "source": "linkedin",
                "industry": "Tecnologia"
            },
            {
                "name": "Maria Santos",
                "title": "Diretora de Vendas",
                "company": "SalesCorp",
                "email": "maria@salescorp.com",
                "source": "website",
                "industry": "Vendas"
            }
        ]
        
        # Export to CSV
        csv_file = self.temp_path / "leads_export.csv"
        headers = ["name", "title", "company", "email", "source", "industry"]
        write_csv_file(str(csv_file), leads_csv_data, headers=headers)
        
        # Read back and verify
        imported_data = read_csv_file(str(csv_file), has_headers=True)
        assert len(imported_data) == 2
        assert imported_data[0]["name"] == "João Silva"
        assert imported_data[1]["industry"] == "Vendas"


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_file_handler_error_creation(self):
        """Test FileHandlerError creation"""
        error = FileHandlerError("Test error message", "test_operation")
        assert str(error) == "Test error message"
        assert error.operation == "test_operation"
    
    def test_permission_errors(self):
        """Test handling of permission errors"""
        # This test might be platform-specific
        pass
    
    def test_disk_space_errors(self):
        """Test handling of disk space errors"""
        # This test would require mocking file system
        pass
    
    def test_corrupted_file_handling(self):
        """Test handling of corrupted files"""
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        
        try:
            # Create corrupted JSON file
            corrupted_json = temp_path / "corrupted.json"
            with open(corrupted_json, 'wb') as f:
                f.write(b'\x00\x01\x02\x03')  # Binary data that's not JSON
            
            with pytest.raises(FileHandlerError):
                read_json_file(str(corrupted_json))
                
        finally:
            import shutil
            shutil.rmtree(temp_path)


class TestIntegrationScenarios:
    """Test real-world integration scenarios"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup after each test method"""
        import shutil
        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)
    
    def test_lead_processing_workflow(self):
        """Test complete lead processing file workflow"""
        # 1. Import leads from CSV
        input_csv_data = [
            ["João Silva, CEO da TechCorp, busca automação", "linkedin"],
            ["Maria Santos, diretora de vendas na InnovaCorp", "website"],
            ["Carlos Oliveira procura soluções de IA", "email"]
        ]
        
        input_csv = self.temp_path / "input_leads.csv"
        write_csv_file(str(input_csv), input_csv_data, headers=["source_text", "source"])
        
        # 2. Read and process
        raw_leads = read_csv_file(str(input_csv), has_headers=True)
        assert len(raw_leads) == 3
        
        # 3. Convert to Lead objects (simulate processing)
        processed_leads = []
        for raw_lead in raw_leads:
            lead = Lead(
                source_text=raw_lead["source_text"],
                source=raw_lead["source"]
            )
            processed_leads.append(lead.to_dict())
        
        # 4. Export processed results
        output_json = self.temp_path / "processed_leads.json"
        write_json_file(str(output_json), processed_leads)
        
        # 5. Verify output
        final_data = read_json_file(str(output_json))
        assert len(final_data) == 3
        assert all("lead_id" in lead for lead in final_data)
        assert all("created_at" in lead for lead in final_data)


if __name__ == "__main__":
    pytest.main([__file__])