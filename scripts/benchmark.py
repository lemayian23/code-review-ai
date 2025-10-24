#!/usr/bin/env python3
"""
Benchmark script for Code Review AI
"""
import asyncio
import time
import argparse
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import statistics

import structlog
import httpx
from core.llm.client import LLMClient
from core.patterns.rules import PatternMatcher
from core.rag.retriever import ContextRetriever

logger = structlog.get_logger(__name__)


class BenchmarkRunner:
    """Benchmark runner for Code Review AI"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.pattern_matcher = PatternMatcher()
        self.context_retriever = ContextRetriever()
        self.results = []

    async def benchmark_llm_analysis(self, diff_content: str, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark LLM analysis performance"""
        logger.info("Benchmarking LLM analysis", iterations=iterations)
        
        times = []
        costs = []
        token_usage = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                suggestions = await self.llm_client.analyze_code(
                    diff_content=diff_content,
                    context_docs=[],
                    file_paths=["test.py"],
                    repository_url="https://github.com/test/repo"
                )
                
                processing_time = time.time() - start_time
                times.append(processing_time)
                
                # Estimate cost (simplified)
                cost = len(diff_content) * 0.00001  # Rough estimate
                costs.append(cost)
                
                # Get token usage
                usage = self.llm_client.get_token_usage()
                token_usage.append(usage)
                
                logger.debug("LLM analysis completed", iteration=i+1, time=processing_time)
                
            except Exception as e:
                logger.error("LLM analysis failed", iteration=i+1, error=str(e))
                times.append(float('inf'))
                costs.append(0.0)
        
        return {
            "component": "llm_analysis",
            "iterations": iterations,
            "avg_time": statistics.mean([t for t in times if t != float('inf')]),
            "min_time": min([t for t in times if t != float('inf')]),
            "max_time": max([t for t in times if t != float('inf')]),
            "std_dev": statistics.stdev([t for t in times if t != float('inf')]) if len(times) > 1 else 0,
            "avg_cost": statistics.mean(costs),
            "total_cost": sum(costs),
            "success_rate": len([t for t in times if t != float('inf')]) / iterations
        }

    def benchmark_pattern_matching(self, diff_content: str, iterations: int = 100) -> Dict[str, Any]:
        """Benchmark pattern matching performance"""
        logger.info("Benchmarking pattern matching", iterations=iterations)
        
        times = []
        matches_count = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                matches = self.pattern_matcher.analyze_code(
                    diff_content=diff_content,
                    file_paths=["test.py"]
                )
                
                processing_time = time.time() - start_time
                times.append(processing_time)
                matches_count.append(len(matches))
                
                logger.debug("Pattern matching completed", iteration=i+1, time=processing_time, matches=len(matches))
                
            except Exception as e:
                logger.error("Pattern matching failed", iteration=i+1, error=str(e))
                times.append(float('inf'))
                matches_count.append(0)
        
        return {
            "component": "pattern_matching",
            "iterations": iterations,
            "avg_time": statistics.mean([t for t in times if t != float('inf')]),
            "min_time": min([t for t in times if t != float('inf')]),
            "max_time": max([t for t in times if t != float('inf')]),
            "std_dev": statistics.stdev([t for t in times if t != float('inf')]) if len(times) > 1 else 0,
            "avg_matches": statistics.mean(matches_count),
            "success_rate": len([t for t in times if t != float('inf')]) / iterations
        }

    async def benchmark_context_retrieval(self, diff_content: str, iterations: int = 10) -> Dict[str, Any]:
        """Benchmark context retrieval performance"""
        logger.info("Benchmarking context retrieval", iterations=iterations)
        
        times = []
        documents_count = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                documents = await self.context_retriever.retrieve_context(
                    diff_content=diff_content,
                    file_paths=["test.py"],
                    repository_id="test-repo-id"
                )
                
                processing_time = time.time() - start_time
                times.append(processing_time)
                documents_count.append(len(documents))
                
                logger.debug("Context retrieval completed", iteration=i+1, time=processing_time, documents=len(documents))
                
            except Exception as e:
                logger.error("Context retrieval failed", iteration=i+1, error=str(e))
                times.append(float('inf'))
                documents_count.append(0)
        
        return {
            "component": "context_retrieval",
            "iterations": iterations,
            "avg_time": statistics.mean([t for t in times if t != float('inf')]),
            "min_time": min([t for t in times if t != float('inf')]),
            "max_time": max([t for t in times if t != float('inf')]),
            "std_dev": statistics.stdev([t for t in times if t != float('inf')]) if len(times) > 1 else 0,
            "avg_documents": statistics.mean(documents_count),
            "success_rate": len([t for t in times if t != float('inf')]) / iterations
        }

    async def benchmark_api_endpoints(self, base_url: str, concurrent_requests: int = 10) -> Dict[str, Any]:
        """Benchmark API endpoints"""
        logger.info("Benchmarking API endpoints", concurrent_requests=concurrent_requests)
        
        async def make_request(session: httpx.AsyncClient, endpoint: str) -> Dict[str, Any]:
            start_time = time.time()
            try:
                response = await session.get(f"{base_url}{endpoint}")
                processing_time = time.time() - start_time
                return {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "time": processing_time,
                    "success": response.status_code == 200
                }
            except Exception as e:
                processing_time = time.time() - start_time
                return {
                    "endpoint": endpoint,
                    "status_code": 0,
                    "time": processing_time,
                    "success": False,
                    "error": str(e)
                }
        
        endpoints = ["/health/", "/health/ready", "/health/live", "/metrics"]
        results = []
        
        async with httpx.AsyncClient() as session:
            # Create tasks for concurrent requests
            tasks = []
            for _ in range(concurrent_requests):
                for endpoint in endpoints:
                    tasks.append(make_request(session, endpoint))
            
            # Execute all requests
            results = await asyncio.gather(*tasks)
        
        # Calculate metrics
        successful_requests = [r for r in results if r["success"]]
        times = [r["time"] for r in successful_requests]
        
        return {
            "component": "api_endpoints",
            "total_requests": len(results),
            "successful_requests": len(successful_requests),
            "success_rate": len(successful_requests) / len(results),
            "avg_time": statistics.mean(times) if times else 0,
            "min_time": min(times) if times else 0,
            "max_time": max(times) if times else 0,
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0
        }

    async def run_full_benchmark(self, args) -> Dict[str, Any]:
        """Run full benchmark suite"""
        logger.info("Starting full benchmark suite")
        
        # Sample diff content for testing
        sample_diff = """diff --git a/src/auth.py b/src/auth.py
index 1234567..abcdefg 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,6 +10,7 @@ def authenticate_user(username, password):
     user = get_user_by_username(username)
     if user and user.password == password:
+        # TODO: Add password hashing
         return user
     return None
@@ -20,6 +21,8 @@ def create_user(username, password):
-    user = User(username=username, password=password)
+    user = User(username=username, password=password)
+    # Hardcoded password for testing
+    if password == "admin123":
+        return user
     return user"""
        
        results = {
            "benchmark_timestamp": time.time(),
            "args": vars(args),
            "components": []
        }
        
        # Benchmark LLM analysis
        if args.llm_iterations > 0:
            llm_results = await self.benchmark_llm_analysis(sample_diff, args.llm_iterations)
            results["components"].append(llm_results)
        
        # Benchmark pattern matching
        if args.pattern_iterations > 0:
            pattern_results = self.benchmark_pattern_matching(sample_diff, args.pattern_iterations)
            results["components"].append(pattern_results)
        
        # Benchmark context retrieval
        if args.retrieval_iterations > 0:
            retrieval_results = await self.benchmark_context_retrieval(sample_diff, args.retrieval_iterations)
            results["components"].append(retrieval_results)
        
        # Benchmark API endpoints
        if args.api_requests > 0:
            api_results = await self.benchmark_api_endpoints("http://localhost:8000", args.api_requests)
            results["components"].append(api_results)
        
        logger.info("Benchmark suite completed", components=len(results["components"]))
        return results

    def print_results(self, results: Dict[str, Any]):
        """Print benchmark results"""
        print("\n" + "="*60)
        print("CODE REVIEW AI BENCHMARK RESULTS")
        print("="*60)
        
        for component in results["components"]:
            print(f"\n{component['component'].upper()}:")
            print(f"  Iterations: {component['iterations']}")
            print(f"  Average Time: {component['avg_time']:.3f}s")
            print(f"  Min Time: {component['min_time']:.3f}s")
            print(f"  Max Time: {component['max_time']:.3f}s")
            print(f"  Std Dev: {component['std_dev']:.3f}s")
            
            if 'success_rate' in component:
                print(f"  Success Rate: {component['success_rate']:.1%}")
            
            if 'avg_cost' in component:
                print(f"  Average Cost: ${component['avg_cost']:.6f}")
                print(f"  Total Cost: ${component['total_cost']:.6f}")
            
            if 'avg_matches' in component:
                print(f"  Average Matches: {component['avg_matches']:.1f}")
            
            if 'avg_documents' in component:
                print(f"  Average Documents: {component['avg_documents']:.1f}")
        
        print("\n" + "="*60)


async def main():
    """Main benchmark function"""
    parser = argparse.ArgumentParser(description="Benchmark Code Review AI")
    parser.add_argument("--llm-iterations", type=int, default=5, help="Number of LLM analysis iterations")
    parser.add_argument("--pattern-iterations", type=int, default=50, help="Number of pattern matching iterations")
    parser.add_argument("--retrieval-iterations", type=int, default=5, help="Number of context retrieval iterations")
    parser.add_argument("--api-requests", type=int, default=20, help="Number of API requests")
    parser.add_argument("--output", type=str, help="Output file for results")
    
    args = parser.parse_args()
    
    # Run benchmark
    runner = BenchmarkRunner()
    results = await runner.run_full_benchmark(args)
    
    # Print results
    runner.print_results(results)
    
    # Save results if output file specified
    if args.output:
        import json
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("Results saved", output_file=args.output)


if __name__ == "__main__":
    asyncio.run(main())
