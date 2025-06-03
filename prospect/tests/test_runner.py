"""
Comprehensive test runner for Nellia Prospector
Runs all tests with coverage reporting and performance metrics.
"""

import pytest
import sys
import os
import time
from pathlib import Path
from typing import Dict, Any, List
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class TestRunner:
    """Enhanced test runner with reporting capabilities"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
    def run_all_tests(self, verbose: bool = True, coverage: bool = True) -> Dict[str, Any]:
        """Run all tests with optional coverage"""
        print("🚀 Starting Nellia Prospector Test Suite")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # Build pytest arguments
        pytest_args = [
            str(Path(__file__).parent),  # Test directory
            "-v" if verbose else "-q",   # Verbose or quiet
            "--tb=short",                # Short traceback format
            "--strict-markers",          # Strict marker checking
            "--disable-warnings"         # Disable warnings for cleaner output
        ]
        
        # Add coverage if requested
        if coverage:
            pytest_args.extend([
                "--cov=.",
                "--cov-report=term-missing",
                "--cov-report=html:tests/coverage_html",
                "--cov-report=json:tests/coverage.json"
            ])
        
        # Run tests
        print(f"Running tests with args: {' '.join(pytest_args)}")
        exit_code = pytest.main(pytest_args)
        
        self.end_time = time.time()
        
        # Generate results
        results = self._generate_results(exit_code)
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def run_specific_tests(self, test_files: List[str], verbose: bool = True) -> Dict[str, Any]:
        """Run specific test files"""
        print(f"🎯 Running specific tests: {', '.join(test_files)}")
        print("=" * 60)
        
        self.start_time = time.time()
        
        # Build test paths
        test_paths = []
        for test_file in test_files:
            test_path = Path(__file__).parent / test_file
            if test_path.exists():
                test_paths.append(str(test_path))
            else:
                print(f"⚠️  Test file not found: {test_file}")
        
        if not test_paths:
            print("❌ No valid test files found")
            return {"success": False, "error": "No valid test files"}
        
        # Run tests
        pytest_args = test_paths + ["-v" if verbose else "-q", "--tb=short"]
        exit_code = pytest.main(pytest_args)
        
        self.end_time = time.time()
        
        results = self._generate_results(exit_code)
        self._print_summary(results)
        
        return results
    
    def run_unit_tests(self) -> Dict[str, Any]:
        """Run only unit tests (excluding integration tests)"""
        print("🧪 Running Unit Tests Only")
        print("=" * 60)
        
        unit_test_files = [
            "test_config.py",
            "test_data_models.py", 
            "test_nlp_utils.py",
            "test_validators.py",
            "test_file_handler.py"
        ]
        
        return self.run_specific_tests(unit_test_files)
    
    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        print("🔗 Running Integration Tests")
        print("=" * 60)
        
        integration_test_files = [
            "test_agents_integration.py",
            "test_pipeline_integration.py",
            "test_llm_integration.py"
        ]
        
        return self.run_specific_tests(integration_test_files)
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests"""
        print("⚡ Running Performance Tests")
        print("=" * 60)
        
        performance_test_files = [
            "test_performance.py"
        ]
        
        return self.run_specific_tests(performance_test_files)
    
    def _generate_results(self, exit_code: int) -> Dict[str, Any]:
        """Generate test results summary"""
        duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        results = {
            "success": exit_code == 0,
            "exit_code": exit_code,
            "duration_seconds": round(duration, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_files_run": self._get_test_files(),
            "coverage_available": self._check_coverage_available()
        }
        
        # Try to load coverage data if available
        if results["coverage_available"]:
            try:
                coverage_data = self._load_coverage_data()
                results["coverage"] = coverage_data
            except Exception as e:
                results["coverage_error"] = str(e)
        
        return results
    
    def _get_test_files(self) -> List[str]:
        """Get list of test files in the test directory"""
        test_dir = Path(__file__).parent
        test_files = []
        
        for test_file in test_dir.glob("test_*.py"):
            if test_file.name != "test_runner.py":
                test_files.append(test_file.name)
        
        return sorted(test_files)
    
    def _check_coverage_available(self) -> bool:
        """Check if coverage data is available"""
        coverage_file = Path(__file__).parent / "coverage.json"
        return coverage_file.exists()
    
    def _load_coverage_data(self) -> Dict[str, Any]:
        """Load coverage data from JSON file"""
        coverage_file = Path(__file__).parent / "coverage.json"
        
        with open(coverage_file, 'r') as f:
            coverage_data = json.load(f)
        
        # Extract summary
        summary = coverage_data.get("totals", {})
        
        return {
            "coverage_percent": round(summary.get("percent_covered", 0), 2),
            "lines_covered": summary.get("covered_lines", 0),
            "lines_total": summary.get("num_statements", 0),
            "missing_lines": summary.get("missing_lines", 0),
            "files_covered": len(coverage_data.get("files", {}))
        }
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        status = "✅ PASSED" if results["success"] else "❌ FAILED"
        print(f"Status: {status}")
        print(f"Duration: {results['duration_seconds']}s")
        print(f"Timestamp: {results['timestamp']}")
        
        if "coverage" in results:
            coverage = results["coverage"]
            print(f"Coverage: {coverage['coverage_percent']}%")
            print(f"Lines Covered: {coverage['lines_covered']}/{coverage['lines_total']}")
        
        print(f"Test Files: {len(results['test_files_run'])}")
        for test_file in results["test_files_run"]:
            print(f"  • {test_file}")
        
        if not results["success"]:
            print(f"\n❌ Tests failed with exit code: {results['exit_code']}")
            print("💡 Check the output above for details")
        else:
            print("\n🎉 All tests passed successfully!")
        
        print("=" * 60)


def main():
    """Main function for running tests from command line"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nellia Prospector Test Runner")
    parser.add_argument("--type", choices=["all", "unit", "integration", "performance"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--files", nargs="+", help="Specific test files to run")
    parser.add_argument("--no-coverage", action="store_true", help="Disable coverage reporting")
    parser.add_argument("--quiet", action="store_true", help="Run tests in quiet mode")
    parser.add_argument("--save-results", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Determine which tests to run
    if args.files:
        results = runner.run_specific_tests(args.files, verbose=not args.quiet)
    elif args.type == "unit":
        results = runner.run_unit_tests()
    elif args.type == "integration":
        results = runner.run_integration_tests()
    elif args.type == "performance":
        results = runner.run_performance_tests()
    else:  # all
        results = runner.run_all_tests(verbose=not args.quiet, coverage=not args.no_coverage)
    
    # Save results if requested
    if args.save_results:
        with open(args.save_results, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"📄 Results saved to: {args.save_results}")
    
    # Exit with appropriate code
    sys.exit(0 if results["success"] else 1)


if __name__ == "__main__":
    main()