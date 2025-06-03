#!/usr/bin/env python3
"""
Test script to verify Nellia Prospector installation and setup.
Run this after installation to ensure everything is working correctly.
"""

import sys
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def test_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        return True, f"Python {version.major}.{version.minor}.{version.micro}"
    return False, f"Python {version.major}.{version.minor} (3.8+ required)"


def test_imports():
    """Test critical imports"""
    imports = {
        "pydantic": "Data validation",
        "loguru": "Logging",
        "click": "CLI framework",
        "rich": "Terminal UI",
        "google.generativeai": "Gemini API"
    }
    
    results = {}
    for module, description in imports.items():
        try:
            __import__(module)
            results[module] = (True, description)
        except ImportError:
            results[module] = (False, f"{description} - NOT INSTALLED")
    
    return results


def test_project_structure():
    """Check project structure"""
    required_dirs = ["agents", "core_logic", "data_models", "utils", "harvester_output"]
    required_files = ["main.py", "requirements.txt", "README.md"]
    
    results = {}
    
    for dir_name in required_dirs:
        exists = Path(dir_name).is_dir()
        results[f"Directory: {dir_name}"] = (exists, "Required directory")
    
    for file_name in required_files:
        exists = Path(file_name).is_file()
        results[f"File: {file_name}"] = (exists, "Required file")
    
    return results


def test_environment():
    """Check environment variables"""
    env_vars = {
        "GEMINI_API_KEY": "Google Gemini API key",
        "GOOGLE_API_KEY": "Alternative Google API key",
        "OPENAI_API_KEY": "OpenAI API key (optional)"
    }
    
    results = {}
    has_any_key = False
    
    for var, description in env_vars.items():
        value = os.getenv(var)
        if value:
            # Mask the API key for security
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            results[var] = (True, f"{description} (configured: {masked})")
            if var in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY"]:
                has_any_key = True
        else:
            optional = "(optional)" in description
            results[var] = (optional, f"{description} - NOT SET")
    
    return results, has_any_key


def test_example_data():
    """Check for example data"""
    harvester_dir = Path("harvester_output")
    if harvester_dir.exists():
        json_files = list(harvester_dir.glob("*.json"))
        if json_files:
            return True, f"Found {len(json_files)} example JSON file(s)"
        return False, "No JSON files found in harvester_output/"
    return False, "harvester_output/ directory not found"


def run_tests():
    """Run all tests and display results"""
    console.print(Panel.fit(
        "[bold cyan]Nellia Prospector - Installation Test[/bold cyan]\n"
        "Checking your setup...",
        border_style="cyan"
    ))
    
    all_passed = True
    
    # Test Python version
    console.print("\n[bold]1. Python Version Check[/bold]")
    passed, message = test_python_version()
    if passed:
        console.print(f"  ✅ {message}")
    else:
        console.print(f"  ❌ {message}")
        all_passed = False
    
    # Test imports
    console.print("\n[bold]2. Required Packages[/bold]")
    import_results = test_imports()
    for module, (passed, message) in import_results.items():
        if passed:
            console.print(f"  ✅ {module}: {message}")
        else:
            console.print(f"  ❌ {module}: {message}")
            all_passed = False
    
    # Test project structure
    console.print("\n[bold]3. Project Structure[/bold]")
    structure_results = test_project_structure()
    for item, (passed, message) in structure_results.items():
        if passed:
            console.print(f"  ✅ {item}")
        else:
            console.print(f"  ❌ {item} - MISSING")
            all_passed = False
    
    # Test environment
    console.print("\n[bold]4. Environment Variables[/bold]")
    env_results, has_api_key = test_environment()
    for var, (passed, message) in env_results.items():
        if passed:
            console.print(f"  ✅ {var}: {message}")
        else:
            console.print(f"  ⚠️  {var}: {message}")
    
    if not has_api_key:
        console.print("\n  [red]❌ No API keys found! At least one LLM API key is required.[/red]")
        all_passed = False
    
    # Test example data
    console.print("\n[bold]5. Example Data[/bold]")
    passed, message = test_example_data()
    if passed:
        console.print(f"  ✅ {message}")
    else:
        console.print(f"  ⚠️  {message}")
    
    # Summary
    console.print("\n" + "="*50)
    if all_passed:
        console.print(Panel.fit(
            "[bold green]✅ All tests passed![/bold green]\n\n"
            "Your installation is ready. You can now run:\n"
            "[cyan]python main.py harvester_output/[your-file].json -p \"Your product/service\"[/cyan]",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            "[bold red]❌ Some tests failed![/bold red]\n\n"
            "Please fix the issues above before running the system.\n"
            "1. Install missing packages: [cyan]pip install -r requirements.txt[/cyan]\n"
            "2. Set up environment variables in .env file\n"
            "3. Ensure all required directories exist",
            border_style="red"
        ))
    
    return all_passed


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 