"""
Code chunking for RAG system
"""
import hashlib
import ast
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CodeChunk:
    """Code chunk data structure"""
    content: str
    file_path: str
    function_name: Optional[str]
    class_name: Optional[str]
    line_start: int
    line_end: int
    language: str
    complexity_score: float
    hash: str


class CodeChunker:
    """Chunk code into meaningful segments for embedding"""
    
    def __init__(self):
        self.max_chunk_size = 200  # tokens
        self.overlap_size = 50     # tokens
        self.supported_languages = ["python", "javascript", "typescript", "java", "go", "rust"]

    def chunk_code(self, code_content: str, file_path: str) -> List[CodeChunk]:
        """
        Chunk code content into meaningful segments
        """
        try:
            logger.debug("Chunking code", file_path=file_path, content_length=len(code_content))
            
            # Detect language from file extension
            language = self._detect_language(file_path)
            
            # Parse code based on language
            if language == "python":
                chunks = self._chunk_python_code(code_content, file_path, language)
            elif language in ["javascript", "typescript"]:
                chunks = self._chunk_js_code(code_content, file_path, language)
            else:
                chunks = self._chunk_generic_code(code_content, file_path, language)
            
            logger.debug("Code chunking completed", chunks_count=len(chunks))
            return chunks
            
        except Exception as e:
            logger.error("Code chunking failed", file_path=file_path, error=str(e))
            return []

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file path"""
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".jsx": "javascript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust"
        }
        
        for ext, lang in extension_map.items():
            if file_path.endswith(ext):
                return lang
        
        return "unknown"

    def _chunk_python_code(self, code_content: str, file_path: str, language: str) -> List[CodeChunk]:
        """Chunk Python code using AST parsing"""
        try:
            # Parse Python code
            tree = ast.parse(code_content)
            chunks = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    chunk = self._create_function_chunk(node, code_content, file_path, language)
                    if chunk:
                        chunks.append(chunk)
                elif isinstance(node, ast.ClassDef):
                    chunk = self._create_class_chunk(node, code_content, file_path, language)
                    if chunk:
                        chunks.append(chunk)
            
            # If no functions/classes found, create generic chunks
            if not chunks:
                chunks = self._chunk_generic_code(code_content, file_path, language)
            
            return chunks
            
        except SyntaxError as e:
            logger.warning("Python syntax error", file_path=file_path, error=str(e))
            return self._chunk_generic_code(code_content, file_path, language)

    def _create_function_chunk(
        self, 
        node: ast.FunctionDef, 
        code_content: str, 
        file_path: str, 
        language: str
    ) -> Optional[CodeChunk]:
        """Create chunk for Python function"""
        try:
            # Get function source code
            lines = code_content.split('\n')
            function_lines = lines[node.lineno-1:node.end_lineno]
            function_content = '\n'.join(function_lines)
            
            # Calculate complexity
            complexity = self._calculate_complexity(node)
            
            # Create hash
            content_hash = hashlib.sha256(function_content.encode()).hexdigest()
            
            return CodeChunk(
                content=function_content,
                file_path=file_path,
                function_name=node.name,
                class_name=None,
                line_start=node.lineno,
                line_end=node.end_lineno,
                language=language,
                complexity_score=complexity,
                hash=content_hash
            )
            
        except Exception as e:
            logger.warning("Failed to create function chunk", function_name=node.name, error=str(e))
            return None

    def _create_class_chunk(
        self, 
        node: ast.ClassDef, 
        code_content: str, 
        file_path: str, 
        language: str
    ) -> Optional[CodeChunk]:
        """Create chunk for Python class"""
        try:
            # Get class source code
            lines = code_content.split('\n')
            class_lines = lines[node.lineno-1:node.end_lineno]
            class_content = '\n'.join(class_lines)
            
            # Calculate complexity
            complexity = self._calculate_complexity(node)
            
            # Create hash
            content_hash = hashlib.sha256(class_content.encode()).hexdigest()
            
            return CodeChunk(
                content=class_content,
                file_path=file_path,
                function_name=None,
                class_name=node.name,
                line_start=node.lineno,
                line_end=node.end_lineno,
                language=language,
                complexity_score=complexity,
                hash=content_hash
            )
            
        except Exception as e:
            logger.warning("Failed to create class chunk", class_name=node.name, error=str(e))
            return None

    def _chunk_js_code(self, code_content: str, file_path: str, language: str) -> List[CodeChunk]:
        """Chunk JavaScript/TypeScript code"""
        # Simple regex-based chunking for JS/TS
        import re
        
        chunks = []
        lines = code_content.split('\n')
        
        # Find function patterns
        function_pattern = r'^(export\s+)?(async\s+)?function\s+(\w+)'
        class_pattern = r'^(export\s+)?class\s+(\w+)'
        
        current_chunk = []
        current_function = None
        current_class = None
        brace_count = 0
        start_line = 0
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Check for function start
            func_match = re.match(function_pattern, line.strip())
            if func_match and brace_count == 0:
                # Save previous chunk if exists
                if current_chunk and current_function:
                    chunk = self._create_js_chunk(
                        current_chunk, file_path, current_function, 
                        current_class, start_line, line_num-1, language
                    )
                    if chunk:
                        chunks.append(chunk)
                
                # Start new function chunk
                current_chunk = [line]
                current_function = func_match.group(3)
                current_class = None
                start_line = line_num
                brace_count = line.count('{') - line.count('}')
            
            # Check for class start
            elif re.match(class_pattern, line.strip()) and brace_count == 0:
                # Save previous chunk if exists
                if current_chunk and current_function:
                    chunk = self._create_js_chunk(
                        current_chunk, file_path, current_function,
                        current_class, start_line, line_num-1, language
                    )
                    if chunk:
                        chunks.append(chunk)
                
                # Start new class chunk
                current_chunk = [line]
                current_function = None
                current_class = re.match(class_pattern, line.strip()).group(2)
                start_line = line_num
                brace_count = line.count('{') - line.count('}')
            
            else:
                current_chunk.append(line)
                brace_count += line.count('{') - line.count('}')
                
                # End of function/class
                if brace_count == 0 and current_chunk:
                    chunk = self._create_js_chunk(
                        current_chunk, file_path, current_function,
                        current_class, start_line, line_num, language
                    )
                    if chunk:
                        chunks.append(chunk)
                    current_chunk = []
                    current_function = None
                    current_class = None
        
        # Handle remaining chunk
        if current_chunk and current_function:
            chunk = self._create_js_chunk(
                current_chunk, file_path, current_function,
                current_class, start_line, len(lines), language
            )
            if chunk:
                chunks.append(chunk)
        
        return chunks

    def _create_js_chunk(
        self, 
        chunk_lines: List[str], 
        file_path: str, 
        function_name: Optional[str],
        class_name: Optional[str],
        start_line: int,
        end_line: int,
        language: str
    ) -> Optional[CodeChunk]:
        """Create chunk for JavaScript/TypeScript code"""
        try:
            content = '\n'.join(chunk_lines)
            complexity = self._calculate_js_complexity(content)
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            return CodeChunk(
                content=content,
                file_path=file_path,
                function_name=function_name,
                class_name=class_name,
                line_start=start_line,
                line_end=end_line,
                language=language,
                complexity_score=complexity,
                hash=content_hash
            )
            
        except Exception as e:
            logger.warning("Failed to create JS chunk", error=str(e))
            return None

    def _chunk_generic_code(self, code_content: str, file_path: str, language: str) -> List[CodeChunk]:
        """Generic chunking for unsupported languages"""
        lines = code_content.split('\n')
        chunks = []
        
        # Create chunks of reasonable size
        chunk_size = 50  # lines per chunk
        overlap = 10     # lines overlap
        
        for i in range(0, len(lines), chunk_size - overlap):
            chunk_lines = lines[i:i + chunk_size]
            content = '\n'.join(chunk_lines)
            
            if content.strip():
                complexity = self._calculate_generic_complexity(content)
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                
                chunk = CodeChunk(
                    content=content,
                    file_path=file_path,
                    function_name=None,
                    class_name=None,
                    line_start=i + 1,
                    line_end=min(i + chunk_size, len(lines)),
                    language=language,
                    complexity_score=complexity,
                    hash=content_hash
                )
                chunks.append(chunk)
        
        return chunks

    def _calculate_complexity(self, node: ast.AST) -> float:
        """Calculate cyclomatic complexity for AST node"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return min(complexity / 10.0, 1.0)  # Normalize to 0-1

    def _calculate_js_complexity(self, content: str) -> float:
        """Calculate complexity for JavaScript/TypeScript code"""
        complexity = 1
        
        # Count control flow statements
        complexity += content.count('if ') + content.count('while ') + content.count('for ')
        complexity += content.count('switch ') + content.count('case ')
        complexity += content.count('catch ') + content.count('finally ')
        complexity += content.count('&&') + content.count('||')
        
        return min(complexity / 20.0, 1.0)  # Normalize to 0-1

    def _calculate_generic_complexity(self, content: str) -> float:
        """Calculate complexity for generic code"""
        complexity = 1
        
        # Count common control flow patterns
        complexity += content.count('if ') + content.count('while ') + content.count('for ')
        complexity += content.count('switch ') + content.count('case ')
        complexity += content.count('&&') + content.count('||')
        
        return min(complexity / 15.0, 1.0)  # Normalize to 0-1

    def get_chunking_stats(self) -> Dict[str, Any]:
        """Get chunking statistics"""
        return {
            "max_chunk_size": self.max_chunk_size,
            "overlap_size": self.overlap_size,
            "supported_languages": self.supported_languages
        }
