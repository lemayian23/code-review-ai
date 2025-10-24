"""
Unit tests for pattern matcher
"""
import pytest
from core.patterns.rules import PatternMatcher, PatternMatch


class TestPatternMatcher:
    """Test cases for pattern matcher"""
    
    @pytest.fixture
    def pattern_matcher(self):
        """Create pattern matcher instance"""
        return PatternMatcher()
    
    @pytest.fixture
    def sample_diff(self):
        """Sample diff content for testing"""
        return """diff --git a/src/auth.py b/src/auth.py
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

    def test_analyze_code_basic(self, pattern_matcher, sample_diff):
        """Test basic code analysis"""
        file_paths = ["src/auth.py"]
        matches = pattern_matcher.analyze_code(sample_diff, file_paths)
        
        assert isinstance(matches, list)
        # Should find hardcoded password pattern
        hardcoded_matches = [m for m in matches if m.rule_name == "hardcoded_password"]
        assert len(hardcoded_matches) > 0

    def test_analyze_code_empty_diff(self, pattern_matcher):
        """Test analysis with empty diff"""
        matches = pattern_matcher.analyze_code("", [])
        assert matches == []

    def test_analyze_code_no_matches(self, pattern_matcher):
        """Test analysis with no pattern matches"""
        clean_diff = """diff --git a/src/clean.py b/src/clean.py
index 1111111..2222222 100644
--- a/src/clean.py
+++ b/src/clean.py
@@ -1,3 +1,3 @@
 def clean_function():
-    return "old"
+    return "new"
"""
        matches = pattern_matcher.analyze_code(clean_diff, ["src/clean.py"])
        assert len(matches) == 0

    def test_add_custom_rule_success(self, pattern_matcher):
        """Test adding custom rule successfully"""
        result = pattern_matcher.add_custom_rule(
            name="test_rule",
            pattern=r"test\s+pattern",
            message="Test pattern found",
            severity="low",
            suggestion="Fix test pattern",
            confidence=0.8
        )
        
        assert result is True
        assert any(rule["name"] == "test_rule" for rule in pattern_matcher.rules)

    def test_add_custom_rule_invalid_regex(self, pattern_matcher):
        """Test adding custom rule with invalid regex"""
        result = pattern_matcher.add_custom_rule(
            name="invalid_rule",
            pattern=r"[invalid regex",
            message="Invalid pattern",
            severity="low",
            suggestion="Fix pattern",
            confidence=0.5
        )
        
        assert result is False
        assert not any(rule["name"] == "invalid_rule" for rule in pattern_matcher.rules)

    def test_remove_rule_success(self, pattern_matcher):
        """Test removing rule successfully"""
        # Add a test rule first
        pattern_matcher.add_custom_rule(
            name="test_rule_to_remove",
            pattern=r"test",
            message="Test",
            severity="low",
            suggestion="Test"
        )
        
        result = pattern_matcher.remove_rule("test_rule_to_remove")
        assert result is True
        assert not any(rule["name"] == "test_rule_to_remove" for rule in pattern_matcher.rules)

    def test_remove_rule_not_found(self, pattern_matcher):
        """Test removing non-existent rule"""
        result = pattern_matcher.remove_rule("non_existent_rule")
        assert result is True  # Should not raise error

    def test_update_rule_from_feedback(self, pattern_matcher):
        """Test updating rules from feedback"""
        feedback_data = [
            {"helpful": False, "rule_name": "hardcoded_password"},
            {"helpful": True, "rule_name": "null_check_missing"},
            {"helpful": False, "rule_name": "hardcoded_password"}
        ]
        
        # Get initial confidence for hardcoded_password rule
        initial_rule = next(rule for rule in pattern_matcher.rules if rule["name"] == "hardcoded_password")
        initial_confidence = initial_rule["confidence"]
        
        updates = pattern_matcher.update_rule_from_feedback(feedback_data)
        
        # Should have updated confidence for hardcoded_password rule
        updated_rule = next(rule for rule in pattern_matcher.rules if rule["name"] == "hardcoded_password")
        assert updated_rule["confidence"] < initial_confidence
        assert updates > 0

    def test_get_rule_stats(self, pattern_matcher):
        """Test getting rule statistics"""
        stats = pattern_matcher.get_rule_stats()
        
        assert "total_rules" in stats
        assert "active_rules" in stats
        assert "rule_performance" in stats
        assert "average_confidence" in stats
        assert stats["total_rules"] > 0

    def test_get_high_performing_rules(self, pattern_matcher):
        """Test getting high performing rules"""
        high_performing = pattern_matcher.get_high_performing_rules(threshold=0.8)
        
        assert isinstance(high_performing, list)
        assert all(rule["confidence"] >= 0.8 for rule in high_performing)

    def test_optimize_rules(self, pattern_matcher):
        """Test rule optimization"""
        # Add some test rules with different performance
        pattern_matcher.add_custom_rule(
            name="high_performing",
            pattern=r"high",
            message="High performance",
            severity="low",
            suggestion="Test",
            confidence=0.5
        )
        
        # Simulate high performance
        pattern_matcher.rule_stats["high_performing"] = {"matches": 8, "total": 10}
        
        optimizations = pattern_matcher.optimize_rules()
        assert optimizations >= 0

    def test_export_rules(self, pattern_matcher):
        """Test exporting rules"""
        rules = pattern_matcher.export_rules()
        
        assert isinstance(rules, list)
        assert len(rules) > 0
        assert all("name" in rule for rule in rules)

    def test_import_rules(self, pattern_matcher):
        """Test importing rules"""
        new_rules = [
            {
                "name": "imported_rule_1",
                "pattern": r"imported1",
                "message": "Imported rule 1",
                "severity": "low",
                "suggestion": "Fix imported 1",
                "confidence": 0.7
            },
            {
                "name": "imported_rule_2",
                "pattern": r"imported2",
                "message": "Imported rule 2",
                "severity": "medium",
                "suggestion": "Fix imported 2",
                "confidence": 0.8
            }
        ]
        
        imported_count = pattern_matcher.import_rules(new_rules)
        
        assert imported_count == 2
        assert any(rule["name"] == "imported_rule_1" for rule in pattern_matcher.rules)
        assert any(rule["name"] == "imported_rule_2" for rule in pattern_matcher.rules)

    def test_pattern_match_creation(self):
        """Test PatternMatch dataclass"""
        match = PatternMatch(
            rule_name="test_rule",
            severity="high",
            message="Test message",
            line_number=10,
            file_path="test.py",
            suggestion="Test suggestion",
            confidence=0.8
        )
        
        assert match.rule_name == "test_rule"
        assert match.severity == "high"
        assert match.confidence == 0.8

    def test_rule_statistics_tracking(self, pattern_matcher):
        """Test rule statistics tracking"""
        # Simulate some rule matches
        pattern_matcher._update_rule_stats("hardcoded_password", True)
        pattern_matcher._update_rule_stats("hardcoded_password", True)
        pattern_matcher._update_rule_stats("hardcoded_password", False)
        
        stats = pattern_matcher.rule_stats["hardcoded_password"]
        assert stats["matches"] == 2
        assert stats["total"] == 3
