"""
Unit tests for LLM client
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from core.llm.client import LLMClient, LLMResponse


class TestLLMClient:
    """Test cases for LLM client"""
    
    @pytest.fixture
    def llm_client(self):
        """Create LLM client instance"""
        return LLMClient()
    
    @pytest.fixture
    def mock_anthropic_response(self):
        """Mock Anthropic response"""
        response = MagicMock()
        response.content = [MagicMock()]
        response.content[0].text = '{"suggestions": [{"type": "bug", "title": "Test issue"}]}'
        response.usage = MagicMock()
        response.usage.input_tokens = 100
        response.usage.output_tokens = 50
        return response
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI response"""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = '{"suggestions": [{"type": "bug", "title": "Test issue"}]}'
        response.usage = MagicMock()
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.total_tokens = 150
        return response

    @pytest.mark.asyncio
    async def test_analyze_code_success(self, llm_client, mock_anthropic_response):
        """Test successful code analysis"""
        with patch.object(llm_client.anthropic_client.messages, 'create', return_value=mock_anthropic_response):
            with patch.object(llm_client.cache, 'get', return_value=None):
                with patch.object(llm_client.cache, 'set', return_value=True):
                    result = await llm_client.analyze_code(
                        diff_content="+def test():\n+    pass",
                        context_docs=[],
                        file_paths=["test.py"],
                        repository_url="https://github.com/test/repo"
                    )
                    
                    assert isinstance(result, list)
                    assert len(result) > 0

    @pytest.mark.asyncio
    async def test_analyze_code_with_cache(self, llm_client):
        """Test code analysis with cache hit"""
        cached_result = [{"type": "bug", "title": "Cached issue"}]
        
        with patch.object(llm_client.cache, 'get', return_value=cached_result):
            result = await llm_client.analyze_code(
                diff_content="+def test():\n+    pass",
                context_docs=[],
                file_paths=["test.py"],
                repository_url="https://github.com/test/repo"
            )
            
            assert result == cached_result

    @pytest.mark.asyncio
    async def test_call_anthropic(self, llm_client, mock_anthropic_response):
        """Test Anthropic API call"""
        with patch.object(llm_client.anthropic_client.messages, 'create', return_value=mock_anthropic_response):
            response = await llm_client._call_anthropic("Test prompt")
            
            assert isinstance(response, LLMResponse)
            assert response.model == "claude-3-5-sonnet-20241022"
            assert response.usage["input_tokens"] == 100
            assert response.usage["output_tokens"] == 50

    @pytest.mark.asyncio
    async def test_call_openai(self, llm_client, mock_openai_response):
        """Test OpenAI API call"""
        with patch.object(llm_client.openai_client.chat.completions, 'create', return_value=mock_openai_response):
            response = await llm_client._call_openai("Test prompt")
            
            assert isinstance(response, LLMResponse)
            assert response.usage["input_tokens"] == 100
            assert response.usage["output_tokens"] == 50

    def test_prepare_context(self, llm_client):
        """Test context preparation"""
        context_docs = [
            {"file_path": "test.py", "content": "def test(): pass"},
            {"file_path": "utils.py", "content": "def util(): pass"}
        ]
        
        context = llm_client._prepare_context(context_docs)
        
        assert "File: test.py" in context
        assert "def test(): pass" in context
        assert "File: utils.py" in context

    def test_generate_cache_key(self, llm_client):
        """Test cache key generation"""
        key1 = llm_client._generate_cache_key("diff1", ["file1.py"])
        key2 = llm_client._generate_cache_key("diff1", ["file1.py"])
        key3 = llm_client._generate_cache_key("diff2", ["file1.py"])
        
        assert key1 == key2  # Same inputs should produce same key
        assert key1 != key3  # Different inputs should produce different keys

    def test_parse_analysis_response_json(self, llm_client):
        """Test JSON response parsing"""
        json_response = '{"suggestions": [{"type": "bug", "title": "Test issue", "severity": "high"}]}'
        result = llm_client._parse_analysis_response(json_response)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["type"] == "bug"

    def test_parse_analysis_response_text(self, llm_client):
        """Test text response parsing"""
        text_response = """**Issue:** Potential null pointer access
**Severity:** medium
**Description:** This could cause a runtime error"""
        
        result = llm_client._parse_analysis_response(text_response)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert "null pointer" in result[0]["title"].lower()

    def test_add_confidence_scores(self, llm_client):
        """Test confidence score addition"""
        suggestions = [
            {"type": "bug", "severity": "high"},
            {"type": "style", "severity": "low"},
            {"type": "security", "severity": "critical", "description": "Very long description that should increase confidence"}
        ]
        
        result = llm_client._add_confidence_scores(suggestions)
        
        assert all("confidence" in suggestion for suggestion in result)
        assert all(0 <= suggestion["confidence"] <= 1 for suggestion in result)

    def test_calculate_cost_anthropic(self, llm_client):
        """Test cost calculation for Anthropic"""
        usage = {"input_tokens": 1000, "output_tokens": 500}
        cost = llm_client._calculate_cost(usage, "anthropic")
        
        assert cost > 0
        assert isinstance(cost, float)

    def test_calculate_cost_openai(self, llm_client):
        """Test cost calculation for OpenAI"""
        usage = {"input_tokens": 1000, "output_tokens": 500}
        cost = llm_client._calculate_cost(usage, "openai")
        
        assert cost > 0
        assert isinstance(cost, float)

    def test_get_token_usage(self, llm_client):
        """Test token usage tracking"""
        llm_client.token_usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        usage = llm_client.get_token_usage()
        
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["total_tokens"] == 150

    def test_reset_token_usage(self, llm_client):
        """Test token usage reset"""
        llm_client.token_usage = {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        llm_client.reset_token_usage()
        
        assert llm_client.token_usage["input_tokens"] == 0
        assert llm_client.token_usage["output_tokens"] == 0
        assert llm_client.token_usage["total_tokens"] == 0
