"""
LLM client for Code Review AI
"""
import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import structlog
import openai
from anthropic import Anthropic

from core.config import get_settings
from core.llm.cache import LLMCache
from core.llm.prompts import PromptManager
from observability.metrics import record_llm_metrics

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class LLMResponse:
    """LLM response data structure"""
    content: str
    model: str
    usage: Dict[str, int]
    cost: float
    processing_time: float
    cached: bool = False


class LLMClient:
    """Unified LLM client for multiple providers"""
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.cache = LLMCache()
        self.prompt_manager = PromptManager()
        self.token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    async def analyze_code(
        self,
        diff_content: str,
        context_docs: List[Dict[str, Any]],
        file_paths: List[str],
        repository_url: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze code changes using LLM
        """
        start_time = time.time()
        
        try:
            logger.info(
                "Starting LLM code analysis",
                file_count=len(file_paths),
                context_docs_count=len(context_docs)
            )

            # Check cache first
            cache_key = self._generate_cache_key(diff_content, file_paths)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info("Using cached LLM result")
                return cached_result

            # Prepare context
            context_text = self._prepare_context(context_docs)
            
            # Get analysis prompt
            prompt = self.prompt_manager.get_analysis_prompt(
                diff_content=diff_content,
                context=context_text,
                file_paths=file_paths,
                repository_url=repository_url
            )

            # Call LLM
            response = await self._call_llm(prompt)
            
            # Parse response
            suggestions = self._parse_analysis_response(response.content)
            
            # Add confidence scores
            suggestions = self._add_confidence_scores(suggestions)
            
            # Cache result
            self.cache.set(cache_key, suggestions, ttl=settings.CACHE_TTL_DAYS * 24 * 3600)
            
            processing_time = time.time() - start_time
            
            # Record metrics
            record_llm_metrics(
                model=response.model,
                usage=response.usage,
                cost=response.cost,
                processing_time=processing_time,
                cached=False
            )

            logger.info(
                "LLM analysis completed",
                suggestions_count=len(suggestions),
                processing_time=processing_time,
                cost=response.cost
            )

            return suggestions

        except Exception as e:
            logger.error("LLM analysis failed", error=str(e))
            raise

    async def _call_llm(self, prompt: str) -> LLMResponse:
        """Call the appropriate LLM based on configuration"""
        start_time = time.time()
        
        try:
            if settings.LLM_MODEL_PRIMARY.startswith("claude"):
                return await self._call_anthropic(prompt)
            elif settings.LLM_MODEL_PRIMARY.startswith("gpt"):
                return await self._call_openai(prompt)
            else:
                raise ValueError(f"Unsupported model: {settings.LLM_MODEL_PRIMARY}")
                
        except Exception as e:
            logger.error("LLM call failed", error=str(e))
            raise

    async def _call_anthropic(self, prompt: str) -> LLMResponse:
        """Call Anthropic Claude"""
        start_time = time.time()
        
        try:
            response = await self.anthropic_client.messages.create(
                model=settings.LLM_MODEL_PRIMARY,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}]
            )
            
            processing_time = time.time() - start_time
            
            # Calculate usage and cost
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
            
            cost = self._calculate_cost(usage, "anthropic")
            
            return LLMResponse(
                content=response.content[0].text,
                model=settings.LLM_MODEL_PRIMARY,
                usage=usage,
                cost=cost,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error("Anthropic API call failed", error=str(e))
            raise

    async def _call_openai(self, prompt: str) -> LLMResponse:
        """Call OpenAI GPT"""
        start_time = time.time()
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.LLM_MODEL_PRIMARY,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                messages=[{"role": "user", "content": prompt}]
            )
            
            processing_time = time.time() - start_time
            
            # Calculate usage and cost
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            cost = self._calculate_cost(usage, "openai")
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=settings.LLM_MODEL_PRIMARY,
                usage=usage,
                cost=cost,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error("OpenAI API call failed", error=str(e))
            raise

    def _prepare_context(self, context_docs: List[Dict[str, Any]]) -> str:
        """Prepare context from retrieved documents"""
        if not context_docs:
            return ""
        
        context_parts = []
        for doc in context_docs[:5]:  # Limit to top 5 most relevant
            context_parts.append(f"File: {doc.get('file_path', 'Unknown')}")
            context_parts.append(f"Content: {doc.get('content', '')}")
            context_parts.append("---")
        
        return "\n".join(context_parts)

    def _generate_cache_key(self, diff_content: str, file_paths: List[str]) -> str:
        """Generate cache key for request"""
        import hashlib
        
        content_hash = hashlib.sha256(
            f"{diff_content}:{':'.join(file_paths)}".encode()
        ).hexdigest()
        
        return f"llm_analysis:{content_hash}"

    def _parse_analysis_response(self, content: str) -> List[Dict[str, Any]]:
        """Parse LLM response into structured suggestions"""
        try:
            # Try to parse as JSON first
            if content.strip().startswith("{"):
                data = json.loads(content)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "suggestions" in data:
                    return data["suggestions"]
            
            # Fallback to text parsing
            return self._parse_text_response(content)
            
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response, using text parsing")
            return self._parse_text_response(content)

    def _parse_text_response(self, content: str) -> List[Dict[str, Any]]:
        """Parse text response into structured suggestions"""
        suggestions = []
        lines = content.split('\n')
        
        current_suggestion = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('**Issue:**') or line.startswith('Issue:'):
                if current_suggestion:
                    suggestions.append(current_suggestion)
                current_suggestion = {
                    "type": "issue",
                    "title": line.replace('**Issue:**', '').replace('Issue:', '').strip(),
                    "description": "",
                    "severity": "medium"
                }
            elif line.startswith('**Severity:**') or line.startswith('Severity:'):
                severity = line.replace('**Severity:**', '').replace('Severity:', '').strip().lower()
                if current_suggestion:
                    current_suggestion["severity"] = severity
            elif line.startswith('**Description:**') or line.startswith('Description:'):
                description = line.replace('**Description:**', '').replace('Description:', '').strip()
                if current_suggestion:
                    current_suggestion["description"] = description
            elif current_suggestion and line:
                # Add to description
                if current_suggestion["description"]:
                    current_suggestion["description"] += " " + line
                else:
                    current_suggestion["description"] = line
        
        if current_suggestion:
            suggestions.append(current_suggestion)
        
        return suggestions

    def _add_confidence_scores(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Add confidence scores to suggestions"""
        for suggestion in suggestions:
            # Simple confidence scoring based on suggestion characteristics
            confidence = 0.5  # Base confidence
            
            # Increase confidence for specific patterns
            if suggestion.get("severity") == "high":
                confidence += 0.2
            elif suggestion.get("severity") == "medium":
                confidence += 0.1
            
            if len(suggestion.get("description", "")) > 50:
                confidence += 0.1
            
            suggestion["confidence"] = min(confidence, 1.0)
        
        return suggestions

    def _calculate_cost(self, usage: Dict[str, int], provider: str) -> float:
        """Calculate cost based on usage and provider"""
        # Simplified cost calculation
        if provider == "anthropic":
            # Claude pricing (approximate)
            input_cost = usage["input_tokens"] * 0.000003
            output_cost = usage["output_tokens"] * 0.000015
        elif provider == "openai":
            # GPT-4 pricing (approximate)
            input_cost = usage["input_tokens"] * 0.00003
            output_cost = usage["output_tokens"] * 0.00006
        else:
            return 0.0
        
        return input_cost + output_cost

    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage"""
        return self.token_usage.copy()

    def reset_token_usage(self):
        """Reset token usage counter"""
        self.token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
