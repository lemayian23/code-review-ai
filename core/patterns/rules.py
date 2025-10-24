"""
Pattern matching rules for Code Review AI
"""
import re
import ast
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PatternMatch:
    """Pattern match result"""
    rule_name: str
    severity: str
    message: str
    line_number: int
    file_path: str
    suggestion: str
    confidence: float


class PatternMatcher:
    """Pattern matching engine for code analysis"""
    
    def __init__(self):
        self.rules = self._load_default_rules()
        self.rule_stats = {}

    def _load_default_rules(self) -> List[Dict[str, Any]]:
        """Load default pattern rules"""
        return [
            {
                "name": "null_check_missing",
                "pattern": r"\.(\w+)\s*=\s*[^=].*[^=]",
                "message": "Potential null pointer access",
                "severity": "medium",
                "suggestion": "Add null check before accessing object properties",
                "confidence": 0.7
            },
            {
                "name": "hardcoded_password",
                "pattern": r"password\s*=\s*['\"][^'\"]+['\"]",
                "message": "Hardcoded password detected",
                "severity": "high",
                "suggestion": "Use environment variables or secure configuration",
                "confidence": 0.9
            },
            {
                "name": "sql_injection",
                "pattern": r"execute\s*\(\s*['\"].*\+.*['\"]",
                "message": "Potential SQL injection vulnerability",
                "severity": "critical",
                "suggestion": "Use parameterized queries or prepared statements",
                "confidence": 0.8
            },
            {
                "name": "long_function",
                "pattern": r"def\s+\w+\([^)]*\):.*(?:\n.*){50,}",
                "message": "Function is too long",
                "severity": "low",
                "suggestion": "Consider breaking into smaller functions",
                "confidence": 0.6
            },
            {
                "name": "magic_number",
                "pattern": r"\b\d{3,}\b",
                "message": "Magic number detected",
                "severity": "low",
                "suggestion": "Use named constants instead of magic numbers",
                "confidence": 0.5
            },
            {
                "name": "empty_catch",
                "pattern": r"except\s+.*:\s*\n\s*pass",
                "message": "Empty catch block",
                "severity": "medium",
                "suggestion": "Handle exceptions appropriately or log them",
                "confidence": 0.8
            },
            {
                "name": "unused_import",
                "pattern": r"import\s+(\w+).*(?:\n.*){10,}",
                "message": "Potentially unused import",
                "severity": "low",
                "suggestion": "Remove unused imports to clean up code",
                "confidence": 0.4
            },
            {
                "name": "deep_nesting",
                "pattern": r"(?:if|for|while|try).*(?:\n\s*){4,}(?:if|for|while|try)",
                "message": "Deep nesting detected",
                "severity": "medium",
                "suggestion": "Consider refactoring to reduce nesting",
                "confidence": 0.7
            }
        ]

    def analyze_code(
        self,
        diff_content: str,
        file_paths: List[str]
    ) -> List[PatternMatch]:
        """
        Analyze code using pattern matching rules
        """
        try:
            logger.debug("Starting pattern analysis", file_count=len(file_paths))
            
            matches = []
            lines = diff_content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                # Skip diff headers
                if line.startswith(('+++', '---', '@@', 'diff')):
                    continue
                
                # Skip added/removed line markers
                if line.startswith(('+', '-')):
                    line = line[1:]  # Remove diff marker
                
                # Apply each rule
                for rule in self.rules:
                    if re.search(rule["pattern"], line, re.IGNORECASE):
                        match = PatternMatch(
                            rule_name=rule["name"],
                            severity=rule["severity"],
                            message=rule["message"],
                            line_number=line_num,
                            file_path=file_paths[0] if file_paths else "unknown",
                            suggestion=rule["suggestion"],
                            confidence=rule["confidence"]
                        )
                        matches.append(match)
                        
                        # Update rule statistics
                        self._update_rule_stats(rule["name"], True)
            
            logger.debug("Pattern analysis completed", matches_count=len(matches))
            return matches
            
        except Exception as e:
            logger.error("Pattern analysis failed", error=str(e))
            return []

    def _update_rule_stats(self, rule_name: str, matched: bool):
        """Update rule statistics"""
        if rule_name not in self.rule_stats:
            self.rule_stats[rule_name] = {"matches": 0, "total": 0}
        
        self.rule_stats[rule_name]["total"] += 1
        if matched:
            self.rule_stats[rule_name]["matches"] += 1

    def add_custom_rule(
        self,
        name: str,
        pattern: str,
        message: str,
        severity: str,
        suggestion: str,
        confidence: float = 0.5
    ) -> bool:
        """Add custom pattern rule"""
        try:
            # Validate pattern
            re.compile(pattern)
            
            rule = {
                "name": name,
                "pattern": pattern,
                "message": message,
                "severity": severity,
                "suggestion": suggestion,
                "confidence": confidence
            }
            
            self.rules.append(rule)
            logger.info("Custom rule added", rule_name=name)
            return True
            
        except re.error as e:
            logger.error("Invalid regex pattern", pattern=pattern, error=str(e))
            return False
        except Exception as e:
            logger.error("Failed to add custom rule", error=str(e))
            return False

    def remove_rule(self, rule_name: str) -> bool:
        """Remove pattern rule"""
        try:
            self.rules = [rule for rule in self.rules if rule["name"] != rule_name]
            logger.info("Rule removed", rule_name=rule_name)
            return True
        except Exception as e:
            logger.error("Failed to remove rule", error=str(e))
            return False

    def update_rule_from_feedback(self, feedback_data: List[Dict[str, Any]]) -> int:
        """Update rules based on feedback data"""
        try:
            updates = 0
            
            for feedback in feedback_data:
                if not feedback.get("helpful", False):
                    # Rule produced false positive, adjust confidence
                    rule_name = feedback.get("rule_name")
                    if rule_name:
                        for rule in self.rules:
                            if rule["name"] == rule_name:
                                # Decrease confidence for false positives
                                rule["confidence"] = max(0.1, rule["confidence"] - 0.1)
                                updates += 1
                                break
            
            logger.info("Rules updated from feedback", updates=updates)
            return updates
            
        except Exception as e:
            logger.error("Rule update from feedback failed", error=str(e))
            return 0

    def get_rule_stats(self) -> Dict[str, Any]:
        """Get rule statistics"""
        total_rules = len(self.rules)
        active_rules = len([rule for rule in self.rules if rule.get("active", True)])
        
        return {
            "total_rules": total_rules,
            "active_rules": active_rules,
            "rule_performance": self.rule_stats,
            "average_confidence": sum(rule["confidence"] for rule in self.rules) / total_rules if total_rules > 0 else 0
        }

    def get_high_performing_rules(self, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Get rules with high performance"""
        return [
            rule for rule in self.rules
            if rule["confidence"] >= threshold
        ]

    def optimize_rules(self) -> int:
        """Optimize rules based on performance"""
        try:
            optimizations = 0
            
            for rule in self.rules:
                rule_name = rule["name"]
                stats = self.rule_stats.get(rule_name, {"matches": 0, "total": 0})
                
                if stats["total"] > 0:
                    hit_rate = stats["matches"] / stats["total"]
                    
                    # Adjust confidence based on hit rate
                    if hit_rate < 0.3:  # Low hit rate
                        rule["confidence"] = max(0.1, rule["confidence"] - 0.1)
                        optimizations += 1
                    elif hit_rate > 0.8:  # High hit rate
                        rule["confidence"] = min(1.0, rule["confidence"] + 0.1)
                        optimizations += 1
            
            logger.info("Rules optimized", optimizations=optimizations)
            return optimizations
            
        except Exception as e:
            logger.error("Rule optimization failed", error=str(e))
            return 0

    def export_rules(self) -> List[Dict[str, Any]]:
        """Export all rules"""
        return self.rules.copy()

    def import_rules(self, rules: List[Dict[str, Any]]) -> int:
        """Import rules from external source"""
        try:
            imported = 0
            
            for rule in rules:
                if self.add_custom_rule(
                    name=rule["name"],
                    pattern=rule["pattern"],
                    message=rule["message"],
                    severity=rule["severity"],
                    suggestion=rule["suggestion"],
                    confidence=rule.get("confidence", 0.5)
                ):
                    imported += 1
            
            logger.info("Rules imported", count=imported)
            return imported
            
        except Exception as e:
            logger.error("Rule import failed", error=str(e))
            return 0
