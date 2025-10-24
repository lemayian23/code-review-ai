#!/usr/bin/env python3
"""
Run evaluations on golden dataset for Code Review AI
"""
import asyncio
import json
import time
from typing import List, Dict, Any
from pathlib import Path

import structlog
from core.llm.client import LLMClient
from core.patterns.rules import PatternMatcher
from core.rag.retriever import ContextRetriever

logger = structlog.get_logger(__name__)


class GoldenDatasetEvaluator:
    """Evaluator for golden dataset"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.pattern_matcher = PatternMatcher()
        self.context_retriever = ContextRetriever()
        self.results = []

    async def load_golden_dataset(self, dataset_path: str) -> List[Dict[str, Any]]:
        """Load golden dataset from file"""
        try:
            with open(dataset_path, 'r') as f:
                dataset = json.load(f)
            
            logger.info("Golden dataset loaded", samples=len(dataset))
            return dataset
            
        except Exception as e:
            logger.error("Failed to load golden dataset", error=str(e))
            return []

    async def evaluate_sample(self, sample: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single sample"""
        start_time = time.time()
        
        try:
            # Extract sample data
            diff_content = sample["diff_content"]
            file_paths = sample.get("file_paths", [])
            expected_suggestions = sample.get("expected_suggestions", [])
            repository_url = sample.get("repository_url", "https://github.com/test/repo")
            
            # Run LLM analysis
            llm_suggestions = await self.llm_client.analyze_code(
                diff_content=diff_content,
                context_docs=[],
                file_paths=file_paths,
                repository_url=repository_url
            )
            
            # Run pattern matching
            pattern_matches = self.pattern_matcher.analyze_code(
                diff_content=diff_content,
                file_paths=file_paths
            )
            
            # Combine results
            all_suggestions = llm_suggestions + [
                {
                    "type": match.rule_name,
                    "title": match.message,
                    "severity": match.severity,
                    "suggestion": match.suggestion,
                    "confidence": match.confidence
                }
                for match in pattern_matches
            ]
            
            # Calculate metrics
            metrics = self._calculate_metrics(all_suggestions, expected_suggestions)
            
            processing_time = time.time() - start_time
            
            result = {
                "sample_id": sample.get("id", "unknown"),
                "processing_time": processing_time,
                "suggestions_generated": len(all_suggestions),
                "expected_suggestions": len(expected_suggestions),
                "metrics": metrics,
                "suggestions": all_suggestions,
                "expected": expected_suggestions
            }
            
            logger.debug("Sample evaluated", sample_id=result["sample_id"], metrics=metrics)
            return result
            
        except Exception as e:
            logger.error("Sample evaluation failed", sample_id=sample.get("id"), error=str(e))
            return {
                "sample_id": sample.get("id", "unknown"),
                "error": str(e),
                "processing_time": time.time() - start_time
            }

    def _calculate_metrics(self, generated: List[Dict[str, Any]], expected: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate evaluation metrics"""
        if not expected:
            return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0}
        
        # Simple matching based on type and title similarity
        true_positives = 0
        false_positives = 0
        
        for gen_suggestion in generated:
            gen_type = gen_suggestion.get("type", "")
            gen_title = gen_suggestion.get("title", "").lower()
            
            matched = False
            for exp_suggestion in expected:
                exp_type = exp_suggestion.get("type", "")
                exp_title = exp_suggestion.get("title", "").lower()
                
                # Check type match and title similarity
                if gen_type == exp_type and self._calculate_similarity(gen_title, exp_title) > 0.5:
                    matched = True
                    break
            
            if matched:
                true_positives += 1
            else:
                false_positives += 1
        
        false_negatives = len(expected) - true_positives
        
        # Calculate metrics
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity (simple implementation)"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)

    async def run_evaluation(self, dataset_path: str) -> Dict[str, Any]:
        """Run full evaluation on golden dataset"""
        logger.info("Starting golden dataset evaluation")
        
        # Load dataset
        dataset = await self.load_golden_dataset(dataset_path)
        if not dataset:
            logger.error("No dataset loaded")
            return {}
        
        # Evaluate each sample
        results = []
        for sample in dataset:
            result = await self.evaluate_sample(sample)
            results.append(result)
        
        # Calculate aggregate metrics
        aggregate_metrics = self._calculate_aggregate_metrics(results)
        
        # Generate report
        report = {
            "evaluation_timestamp": time.time(),
            "total_samples": len(dataset),
            "successful_evaluations": len([r for r in results if "error" not in r]),
            "failed_evaluations": len([r for r in results if "error" in r]),
            "aggregate_metrics": aggregate_metrics,
            "individual_results": results
        }
        
        logger.info("Evaluation completed", report=report)
        return report

    def _calculate_aggregate_metrics(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate aggregate metrics across all results"""
        successful_results = [r for r in results if "error" not in r and "metrics" in r]
        
        if not successful_results:
            return {"precision": 0.0, "recall": 0.0, "f1_score": 0.0, "avg_processing_time": 0.0}
        
        # Calculate averages
        avg_precision = sum(r["metrics"]["precision"] for r in successful_results) / len(successful_results)
        avg_recall = sum(r["metrics"]["recall"] for r in successful_results) / len(successful_results)
        avg_f1 = sum(r["metrics"]["f1_score"] for r in successful_results) / len(successful_results)
        avg_processing_time = sum(r["processing_time"] for r in successful_results) / len(successful_results)
        
        return {
            "precision": avg_precision,
            "recall": avg_recall,
            "f1_score": avg_f1,
            "avg_processing_time": avg_processing_time,
            "total_samples": len(results),
            "successful_samples": len(successful_results)
        }

    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save evaluation results to file"""
        try:
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info("Results saved", output_path=output_path)
            
        except Exception as e:
            logger.error("Failed to save results", error=str(e))


async def main():
    """Main evaluation function"""
    # Create golden dataset if it doesn't exist
    dataset_path = Path("tests/evals/golden_dataset.json")
    if not dataset_path.exists():
        # Create sample golden dataset
        sample_dataset = [
            {
                "id": "sample_1",
                "diff_content": """diff --git a/src/auth.py b/src/auth.py
index 1234567..abcdefg 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,6 +10,7 @@ def authenticate_user(username, password):
     user = get_user_by_username(username)
     if user and user.password == password:
+        # TODO: Add password hashing
         return user
     return None""",
                "file_paths": ["src/auth.py"],
                "repository_url": "https://github.com/test/repo",
                "expected_suggestions": [
                    {
                        "type": "security",
                        "title": "Password hashing missing",
                        "severity": "high",
                        "description": "Passwords should be hashed before storage"
                    }
                ]
            },
            {
                "id": "sample_2",
                "diff_content": """diff --git a/src/utils.py b/src/utils.py
index 1111111..2222222 100644
--- a/src/utils.py
+++ b/src/utils.py
@@ -5,6 +5,8 @@ def calculate_total(items):
     total = 0
     for item in items:
+        if item is None:
+            continue
         total += item.price
     return total""",
                "file_paths": ["src/utils.py"],
                "repository_url": "https://github.com/test/repo",
                "expected_suggestions": [
                    {
                        "type": "bug",
                        "title": "Null check added",
                        "severity": "medium",
                        "description": "Good addition of null check"
                    }
                ]
            }
        ]
        
        with open(dataset_path, 'w') as f:
            json.dump(sample_dataset, f, indent=2)
        
        logger.info("Created sample golden dataset", path=str(dataset_path))
    
    # Run evaluation
    evaluator = GoldenDatasetEvaluator()
    results = await evaluator.run_evaluation(str(dataset_path))
    
    # Save results
    output_path = "tests/evals/evaluation_results.json"
    evaluator.save_results(results, output_path)
    
    # Print summary
    print("\n" + "="*50)
    print("GOLDEN DATASET EVALUATION RESULTS")
    print("="*50)
    print(f"Total samples: {results['total_samples']}")
    print(f"Successful evaluations: {results['successful_evaluations']}")
    print(f"Failed evaluations: {results['failed_evaluations']}")
    print(f"Average precision: {results['aggregate_metrics']['precision']:.3f}")
    print(f"Average recall: {results['aggregate_metrics']['recall']:.3f}")
    print(f"Average F1 score: {results['aggregate_metrics']['f1_score']:.3f}")
    print(f"Average processing time: {results['aggregate_metrics']['avg_processing_time']:.2f}s")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
