#!/usr/bin/env python3
"""
Test runner for Jr Dev Agent services.

This script provides a convenient way to run different types of tests
and check service health before running integration tests.
"""

import os
import sys
import subprocess
import asyncio
import aiohttp
import argparse
import time
from typing import List, Dict, Any, Optional
import json


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class TestRunner:
    """Main test runner class."""
    
    def __init__(self):
        self.services = {
            "mcp_server": "http://localhost:8000",
            "promptbuilder": "http://localhost:8001",
            "template_intelligence": "http://localhost:8002",
            "session_management": "http://localhost:8003",
            "synthetic_memory": "http://localhost:8004",
            "pess": "http://localhost:8005"
        }
        
    def print_header(self, text: str):
        """Print colored header."""
        print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    
    def print_success(self, text: str):
        """Print success message."""
        print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")
    
    def print_warning(self, text: str):
        """Print warning message."""
        print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")
    
    def print_error(self, text: str):
        """Print error message."""
        print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")
    
    def print_info(self, text: str):
        """Print info message."""
        print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")
    
    async def check_service_health(self, service_name: str, url: str) -> bool:
        """Check if a service is healthy."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        self.print_success(f"{service_name} is healthy")
                        return True
                    else:
                        self.print_error(f"{service_name} returned status {response.status}")
                        return False
        except Exception as e:
            self.print_error(f"{service_name} health check failed: {str(e)}")
            return False
    
    async def check_all_services(self) -> Dict[str, bool]:
        """Check health of all services."""
        self.print_header("CHECKING SERVICE HEALTH")
        
        results = {}
        for service_name, url in self.services.items():
            results[service_name] = await self.check_service_health(service_name, url)
        
        healthy_count = sum(results.values())
        total_count = len(results)
        
        if healthy_count == total_count:
            self.print_success(f"All {total_count} services are healthy")
        else:
            self.print_warning(f"{healthy_count}/{total_count} services are healthy")
        
        return results
    
    def run_pytest(self, args: List[str]) -> int:
        """Run pytest with given arguments."""
        cmd = [sys.executable, "-m", "pytest"] + args
        self.print_info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, check=False)
            return result.returncode
        except Exception as e:
            self.print_error(f"Failed to run pytest: {str(e)}")
            return 1
    
    def run_unit_tests(self, verbose: bool = False) -> int:
        """Run unit tests."""
        self.print_header("RUNNING UNIT TESTS")
        
        args = [
            "tests/unit/",
            "-m", "not requires_services",
            "--tb=short"
        ]
        
        if verbose:
            args.append("-v")
        
        return self.run_pytest(args)
    
    def run_integration_tests(self, verbose: bool = False, check_services: bool = True) -> int:
        """Run integration tests."""
        self.print_header("RUNNING INTEGRATION TESTS")
        
        # Check services first if requested
        if check_services:
            service_results = asyncio.run(self.check_all_services())
            healthy_services = [name for name, healthy in service_results.items() if healthy]
            
            if not healthy_services:
                self.print_error("No services are healthy. Cannot run integration tests.")
                return 1
            
            self.print_info(f"Running integration tests for {len(healthy_services)} healthy services")
        
        args = [
            "tests/integration/",
            "--tb=short"
        ]
        
        if verbose:
            args.append("-v")
        
        return self.run_pytest(args)
    
    def run_e2e_tests(self, verbose: bool = False) -> int:
        """Run end-to-end tests."""
        self.print_header("RUNNING E2E TESTS")
        
        # Check all services first
        service_results = asyncio.run(self.check_all_services())
        healthy_count = sum(service_results.values())
        
        if healthy_count < len(self.services):
            self.print_warning(f"Only {healthy_count}/{len(self.services)} services are healthy")
            self.print_warning("E2E tests may fail or be skipped")
        
        args = [
            "tests/e2e/",
            "--tb=short"
        ]
        
        if verbose:
            args.append("-v")
        
        return self.run_pytest(args)
    
    def run_smoke_tests(self, verbose: bool = False) -> int:
        """Run smoke tests."""
        self.print_header("RUNNING SMOKE TESTS")
        
        args = [
            "tests/",
            "-m", "smoke",
            "--tb=short"
        ]
        
        if verbose:
            args.append("-v")
        
        return self.run_pytest(args)
    
    def run_all_tests(self, verbose: bool = False) -> int:
        """Run all tests in sequence."""
        self.print_header("RUNNING ALL TESTS")
        
        # Run unit tests first
        unit_result = self.run_unit_tests(verbose)
        if unit_result != 0:
            self.print_error("Unit tests failed. Stopping.")
            return unit_result
        
        # Run integration tests
        integration_result = self.run_integration_tests(verbose, check_services=True)
        if integration_result != 0:
            self.print_error("Integration tests failed. Stopping.")
            return integration_result
        
        # Run E2E tests
        e2e_result = self.run_e2e_tests(verbose)
        if e2e_result != 0:
            self.print_error("E2E tests failed.")
            return e2e_result
        
        self.print_success("All tests passed!")
        return 0
    
    def run_coverage(self, verbose: bool = False) -> int:
        """Run tests with coverage."""
        self.print_header("RUNNING TESTS WITH COVERAGE")
        
        args = [
            "tests/",
            "--cov=pess_scoring",
            "--cov=promptbuilder", 
            "--cov=template_intelligence",
            "--cov=session_management",
            "--cov=synthetic_memory",
            "--cov=jr_dev_agent",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
            "--tb=short"
        ]
        
        if verbose:
            args.append("-v")
        
        result = self.run_pytest(args)
        
        if result == 0:
            self.print_success("Coverage report generated in htmlcov/")
        
        return result
    
    async def service_status_report(self) -> Dict[str, Any]:
        """Generate detailed service status report."""
        self.print_header("GENERATING SERVICE STATUS REPORT")
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "services": {}
        }
        
        for service_name, url in self.services.items():
            service_info = {
                "name": service_name,
                "url": url,
                "healthy": False,
                "response_time": None,
                "details": {}
            }
            
            try:
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                        response_time = time.time() - start_time
                        service_info["response_time"] = response_time
                        
                        if response.status == 200:
                            service_info["healthy"] = True
                            try:
                                service_info["details"] = await response.json()
                            except:
                                service_info["details"] = {"status": "healthy"}
                            
                            self.print_success(f"{service_name}: {response_time:.3f}s")
                        else:
                            self.print_error(f"{service_name}: HTTP {response.status}")
                            
            except Exception as e:
                self.print_error(f"{service_name}: {str(e)}")
                service_info["error"] = str(e)
            
            report["services"][service_name] = service_info
        
        return report
    
    def print_service_report(self, report: Dict[str, Any]):
        """Print service status report."""
        print(f"\n{Colors.HEADER}SERVICE STATUS REPORT{Colors.ENDC}")
        print(f"Generated: {report['timestamp']}")
        print()
        
        for service_name, info in report["services"].items():
            status = "HEALTHY" if info["healthy"] else "UNHEALTHY"
            color = Colors.OKGREEN if info["healthy"] else Colors.FAIL
            
            print(f"{color}{status:<10}{Colors.ENDC} {service_name:<20} {info['url']}")
            
            if info["response_time"]:
                print(f"           Response time: {info['response_time']:.3f}s")
            
            if info.get("details"):
                details = info["details"]
                if "service" in details:
                    print(f"           Service: {details['service']}")
                if "version" in details:
                    print(f"           Version: {details['version']}")
                if "initialized" in details:
                    print(f"           Initialized: {details['initialized']}")
            
            if info.get("error"):
                print(f"           Error: {info['error']}")
            
            print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Jr Dev Agent Test Runner")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-service-check", action="store_true", help="Skip service health check")
    
    subparsers = parser.add_subparsers(dest="command", help="Test commands")
    
    # Unit tests
    subparsers.add_parser("unit", help="Run unit tests")
    
    # Integration tests
    subparsers.add_parser("integration", help="Run integration tests")
    
    # E2E tests
    subparsers.add_parser("e2e", help="Run end-to-end tests")
    
    # Smoke tests
    subparsers.add_parser("smoke", help="Run smoke tests")
    
    # All tests
    subparsers.add_parser("all", help="Run all tests")
    
    # Coverage
    subparsers.add_parser("coverage", help="Run tests with coverage")
    
    # Health check
    subparsers.add_parser("health", help="Check service health")
    
    # Status report
    subparsers.add_parser("status", help="Generate service status report")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    runner = TestRunner()
    
    try:
        if args.command == "unit":
            return runner.run_unit_tests(args.verbose)
        elif args.command == "integration":
            return runner.run_integration_tests(args.verbose, not args.no_service_check)
        elif args.command == "e2e":
            return runner.run_e2e_tests(args.verbose)
        elif args.command == "smoke":
            return runner.run_smoke_tests(args.verbose)
        elif args.command == "all":
            return runner.run_all_tests(args.verbose)
        elif args.command == "coverage":
            return runner.run_coverage(args.verbose)
        elif args.command == "health":
            results = asyncio.run(runner.check_all_services())
            return 0 if all(results.values()) else 1
        elif args.command == "status":
            report = asyncio.run(runner.service_status_report())
            runner.print_service_report(report)
            
            # Optionally save to file
            with open("service_status_report.json", "w") as f:
                json.dump(report, f, indent=2)
            runner.print_success("Report saved to service_status_report.json")
            return 0
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        runner.print_warning("Test run interrupted by user")
        return 1
    except Exception as e:
        runner.print_error(f"Unexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 