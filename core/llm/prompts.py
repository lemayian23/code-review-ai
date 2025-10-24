"""
Prompt management for Code Review AI
"""
import json
from typing import Dict, Any, List
from dataclasses import dataclass

import structlog
from core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class PromptTemplate:
    """Prompt template data structure"""
    name: str
    template: str
    version: str
    variables: List[str]
    description: str


class PromptManager:
    """Manages prompt templates and versions"""
    
    def __init__(self):
        self.templates = self._load_templates()
        self.current_version = "v1.0"

    def _load_templates(self) -> Dict[str, PromptTemplate]:
        """Load prompt templates"""
        return {
            "analysis": PromptTemplate(
                name="code_analysis",
                template=self._get_analysis_template(),
                version="v1.0",
                variables=["diff_content", "context", "file_paths", "repository_url"],
                description="Main code analysis prompt"
            ),
            "feedback_learning": PromptTemplate(
                name="feedback_learning",
                template=self._get_feedback_learning_template(),
                version="v1.0",
                variables=["feedback_data", "suggestions", "corrections"],
                description="Feedback learning prompt"
            ),
            "pattern_matching": PromptTemplate(
                name="pattern_matching",
                template=self._get_pattern_matching_template(),
                version="v1.0",
                variables=["code_content", "patterns", "rules"],
                description="Pattern matching prompt"
            )
        }

    def get_analysis_prompt(
        self,
        diff_content: str,
        context: str,
        file_paths: List[str],
        repository_url: str
    ) -> str:
        """Get code analysis prompt"""
        template = self.templates["analysis"]
        
        # Format file paths
        file_paths_str = "\n".join([f"- {path}" for path in file_paths])
        
        # Format context
        context_section = f"""
## Context from Repository
{context}
""" if context else ""

        prompt = template.template.format(
            diff_content=diff_content,
            context=context_section,
            file_paths=file_paths_str,
            repository_url=repository_url
        )
        
        logger.debug("Generated analysis prompt", template_version=template.version)
        return prompt

    def get_feedback_learning_prompt(
        self,
        feedback_data: List[Dict[str, Any]],
        suggestions: List[Dict[str, Any]]
    ) -> str:
        """Get feedback learning prompt"""
        template = self.templates["feedback_learning"]
        
        # Format feedback data
        feedback_str = json.dumps(feedback_data, indent=2)
        suggestions_str = json.dumps(suggestions, indent=2)
        
        prompt = template.template.format(
            feedback_data=feedback_str,
            suggestions=suggestions_str
        )
        
        logger.debug("Generated feedback learning prompt", template_version=template.version)
        return prompt

    def get_pattern_matching_prompt(
        self,
        code_content: str,
        patterns: List[Dict[str, Any]]
    ) -> str:
        """Get pattern matching prompt"""
        template = self.templates["pattern_matching"]
        
        # Format patterns
        patterns_str = json.dumps(patterns, indent=2)
        
        prompt = template.template.format(
            code_content=code_content,
            patterns=patterns_str
        )
        
        logger.debug("Generated pattern matching prompt", template_version=template.version)
        return prompt

    def _get_analysis_template(self) -> str:
        """Get code analysis prompt template"""
        return """You are an expert code reviewer analyzing a pull request. Your task is to identify potential issues, improvements, and best practices violations.

## Repository Information
- Repository: {repository_url}
- Changed Files:
{file_paths}

## Code Changes
```diff
{diff_content}
```

{context}

## Analysis Instructions

Please analyze the code changes and provide suggestions in the following JSON format:

```json
[
  {{
    "type": "issue|improvement|style|security|performance",
    "title": "Brief title of the issue",
    "description": "Detailed description of the issue and why it matters",
    "severity": "low|medium|high|critical",
    "line_number": 42,
    "file_path": "src/example.py",
    "suggestion": "Specific code suggestion or fix",
    "category": "bug|style|performance|security|maintainability",
    "confidence": 0.85
  }}
]
```

## Guidelines

1. **Focus on real issues**: Only flag genuine problems, not personal preferences
2. **Be specific**: Provide concrete suggestions and examples
3. **Consider context**: Use the repository context to understand patterns and conventions
4. **Prioritize**: Focus on high-impact issues first
5. **Be constructive**: Provide helpful suggestions, not just criticism

## Categories to Look For

- **Security**: SQL injection, XSS, authentication issues, sensitive data exposure
- **Performance**: N+1 queries, inefficient algorithms, memory leaks
- **Maintainability**: Code duplication, complex functions, unclear naming
- **Style**: Inconsistent formatting, naming conventions, documentation
- **Bugs**: Logic errors, edge cases, null pointer exceptions

Analyze the code and provide your suggestions in the specified JSON format."""

    def _get_feedback_learning_template(self) -> str:
        """Get feedback learning prompt template"""
        return """You are learning from human feedback to improve code review suggestions. Analyze the feedback data and learn patterns to improve future suggestions.

## Feedback Data
{feedback_data}

## Previous Suggestions
{suggestions}

## Learning Task

Based on the feedback data, identify patterns and learnings that can improve future code review suggestions:

1. **What types of suggestions were most helpful?**
2. **What patterns led to false positives?**
3. **How can confidence scoring be improved?**
4. **What new patterns should be recognized?**

Provide insights and recommendations for improving the code review system."""

    def _get_pattern_matching_template(self) -> str:
        """Get pattern matching prompt template"""
        return """You are analyzing code to identify specific patterns and rule violations. Use the provided patterns to detect issues in the code.

## Code Content
{code_content}

## Patterns to Match
{patterns}

## Analysis Task

Analyze the code against the provided patterns and identify any matches or violations. For each match:

1. Identify the specific pattern that was matched
2. Explain why it's a violation or concern
3. Provide a suggested fix or improvement
4. Rate the confidence of the match (0.0 to 1.0)

Return results in JSON format with pattern matches and confidence scores."""

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get prompt template by name"""
        return self.templates.get(name)

    def get_all_templates(self) -> Dict[str, PromptTemplate]:
        """Get all prompt templates"""
        return self.templates.copy()

    def update_template(self, name: str, template: PromptTemplate) -> bool:
        """Update prompt template"""
        try:
            self.templates[name] = template
            logger.info("Template updated", name=name, version=template.version)
            return True
        except Exception as e:
            logger.error("Template update failed", name=name, error=str(e))
            return False

    def validate_template(self, template: str, variables: List[str]) -> bool:
        """Validate template has all required variables"""
        try:
            # Check if all variables are present in template
            for variable in variables:
                if f"{{{variable}}}" not in template:
                    logger.warning("Template missing variable", variable=variable)
                    return False
            return True
        except Exception as e:
            logger.error("Template validation failed", error=str(e))
            return False

    def get_template_stats(self) -> Dict[str, Any]:
        """Get template usage statistics"""
        return {
            "total_templates": len(self.templates),
            "current_version": self.current_version,
            "template_names": list(self.templates.keys())
        }
