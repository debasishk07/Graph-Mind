import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.database import async_session_maker
from app.models.repository import Repository, RepositoryStatus
from app.models.file import File
from app.models.symbol import Symbol, SymbolType
from app.models.relationship import Relationship, RelationshipType
from app.workers.celery_app import celery_app
from app.utils.socketio import emit_progress

settings = get_settings()


@dataclass
class ParsedSymbol:
    name: str
    qualified_name: str
    symbol_type: SymbolType
    start_line: int
    end_line: int
    signature: str
    docstring: Optional[str]
    is_exported: bool
    metadata: Dict = field(default_factory=dict)


@dataclass
class ParsedRelationship:
    source_qualified_name: str
    target_qualified_name: str
    relationship_type: RelationshipType
    line_number: int
    is_dynamic: bool = False


@dataclass
class ParsedFile:
    path: str
    name: str
    extension: str
    language: str
    line_count: int
    size_bytes: int
    symbols: List[ParsedSymbol]
    relationships: List[ParsedRelationship]
    is_entry_point: bool = False
    is_test_file: bool = False
    complexity_score: float = 1.0


# Language detection
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".h": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
}

IGNORE_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "target",
    "venv",
    ".venv",
    "env",
    ".env",
    "vendor",
    "bin",
    "obj",
    ".next",
    ".nuxt",
    "coverage",
    ".coverage",
}

IGNORE_FILES = {
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.so",
    "*.dll",
    "*.class",
    "*.jar",
    "*.war",
    "*.ear",
    "*.min.js",
    "*.min.css",
    "*.map",
}


def detect_language(file_path: str) -> Optional[str]:
    """Detect programming language from file extension."""
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_EXTENSIONS.get(ext)


def is_ignored(path: str) -> bool:
    """Check if path should be ignored."""
    parts = Path(path).parts
    for part in parts:
        if part in IGNORE_DIRS:
            return True
        for pattern in IGNORE_FILES:
            if part.endswith(pattern.replace("*", "")):
                return True
    return False


def count_lines(content: str) -> int:
    """Count non-empty lines in content."""
    return len([line for line in content.splitlines() if line.strip()])


def calculate_complexity(content: str, language: str) -> float:
    """Calculate cyclomatic complexity (simplified)."""
    # This is a simplified version - real implementation would use Tree-sitter
    complexity = 1
    keywords = ["if", "elif", "else", "for", "while", "try", "except", "catch", "case", "switch", "&&", "||", "?"]
    for kw in keywords:
        complexity += content.count(f" {kw} ")
    return min(complexity, 50.0)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def parse_repository_task(self, repository_id: str):
    """Main Celery task to parse a repository."""
    import asyncio

    async def _parse():
        async with async_session_maker() as db:
            await _parse_repository_async(db, UUID(repository_id))

    asyncio.run(_parse())


async def _parse_repository_async(db: AsyncSession, repository_id: UUID):
    """Async repository parsing logic."""
    # Get repository
    result = await db.execute(
        select(Repository).where(Repository.id == repository_id)
    )
    repository = result.scalar_one_or_none()

    if not repository:
        return

    # Update status
    repository.status = RepositoryStatus.PARSING
    repository.status_message = "Scanning files..."
    repository.analysis_progress = 10
    await db.commit()

    await emit_progress(str(repository_id), "scanning", 10, "Scanning files...")

    # Get repository path
    repo_path = repository.storage_path
    if not repo_path or not os.path.exists(repo_path):
        repository.status = RepositoryStatus.ERROR
        repository.status_message = "Repository path not found"
        await db.commit()
        return

    # Scan all files
    files_to_parse = []
    for root, dirs, files in os.walk(repo_path):
        # Filter ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            file_path = os.path.join(root, file)
            if is_ignored(file_path):
                continue

            rel_path = os.path.relpath(file_path, repo_path)
            language = detect_language(file_path)
            if not language:
                continue

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                line_count = count_lines(content)
                size_bytes = os.path.getsize(file_path)

                files_to_parse.append({
                    "path": rel_path,
                    "name": file,
                    "extension": Path(file).suffix,
                    "language": language,
                    "content": content,
                    "line_count": line_count,
                    "size_bytes": size_bytes,
                })
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue

    total_files = len(files_to_parse)
    repository.total_files = total_files
    repository.status_message = f"Found {total_files} files to parse"
    repository.analysis_progress = 20
    await db.commit()

    await emit_progress(str(repository_id), "parsing", 20, f"Found {total_files} files")

    # Parse files
    parsed_files = []
    for idx, file_info in enumerate(files_to_parse):
        try:
            parsed = await parse_file(file_info, repository_id)
            if parsed:
                parsed_files.append(parsed)
        except Exception as e:
            print(f"Error parsing {file_info['path']}: {e}")
            continue

        # Update progress
        progress = 20 + int((idx / total_files) * 60)
        if idx % 10 == 0:
            repository.analysis_progress = progress
            repository.status_message = f"Parsed {idx + 1}/{total_files} files"
            await db.commit()
            await emit_progress(str(repository_id), "parsing", progress, f"Parsed {idx + 1}/{total_files} files")

    # Save to database
    await save_parsed_data(db, repository, parsed_files)

    # Finalize
    repository.status = RepositoryStatus.READY
    repository.status_message = "Analysis complete"
    repository.analysis_progress = 100
    repository.analyzed_at = datetime.utcnow()
    await db.commit()

    await emit_progress(str(repository_id), "ready", 100, "Analysis complete")


async def parse_file(file_info: Dict, repository_id: UUID) -> Optional[ParsedFile]:
    """Parse a single file based on its language."""
    language = file_info["language"]
    content = file_info["content"]

    if language == "python":
        return parse_python_file(file_info, content)
    elif language in ("javascript", "typescript"):
        return parse_js_ts_file(file_info, content, language)
    # Add more languages as needed

    # Fallback: basic parsing
    return ParsedFile(
        path=file_info["path"],
        name=file_info["name"],
        extension=file_info["extension"],
        language=language,
        line_count=file_info["line_count"],
        size_bytes=file_info["size_bytes"],
        symbols=[],
        relationships=[],
    )


def parse_python_file(file_info: Dict, content: str) -> ParsedFile:
    """Parse Python file using Tree-sitter."""
    # Simplified implementation - full Tree-sitter parsing would be more complex
    symbols = []
    relationships = []

    lines = content.splitlines()
    current_class = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Class definitions
        if stripped.startswith("class "):
            parts = stripped.split("(")[0].split()
            if len(parts) >= 2:
                class_name = parts[1].rstrip(":")
                qualified_name = f"{file_info['path']}:{class_name}"
                symbols.append(ParsedSymbol(
                    name=class_name,
                    qualified_name=qualified_name,
                    symbol_type=SymbolType.CLASS,
                    start_line=i,
                    end_line=i,
                    signature=stripped,
                    docstring=None,
                    is_exported=True,
                ))
                current_class = class_name

        # Function definitions
        elif stripped.startswith("def "):
            parts = stripped.split("(")
            if len(parts) >= 2:
                func_name = parts[1].split(")")[0]
                if current_class:
                    qualified_name = f"{file_info['path']}:{current_class}.{func_name}"
                    symbols.append(ParsedSymbol(
                        name=func_name,
                        qualified_name=qualified_name,
                        symbol_type=SymbolType.METHOD,
                        start_line=i,
                        end_line=i,
                        signature=stripped,
                        docstring=None,
                        is_exported=True,
                    ))
                else:
                    qualified_name = f"{file_info['path']}:{func_name}"
                    symbols.append(ParsedSymbol(
                        name=func_name,
                        qualified_name=qualified_name,
                        symbol_type=SymbolType.FUNCTION,
                        start_line=i,
                        end_line=i,
                        signature=stripped,
                        docstring=None,
                        is_exported=True,
                    ))

        # Import statements
        elif stripped.startswith("import ") or stripped.startswith("from "):
            # Extract import relationships
            pass

    return ParsedFile(
        path=file_info["path"],
        name=file_info["name"],
        extension=file_info["extension"],
        language="python",
        line_count=file_info["line_count"],
        size_bytes=file_info["size_bytes"],
        symbols=symbols,
        relationships=relationships,
    )


def parse_js_ts_file(file_info: Dict, content: str, language: str) -> ParsedFile:
    """Parse JavaScript/TypeScript file."""
    symbols = []
    relationships = []

    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Function declarations
        if stripped.startswith("function ") or stripped.startswith("const ") and "=>" in stripped:
            # Simplified extraction
            pass

        # Class declarations
        elif stripped.startswith("class "):
            parts = stripped.split()
            if len(parts) >= 2:
                class_name = parts[1].split("{")[0].split("extends")[0].strip()
                symbols.append(ParsedSymbol(
                    name=class_name,
                    qualified_name=f"{file_info['path']}:{class_name}",
                    symbol_type=SymbolType.CLASS,
                    start_line=i,
                    end_line=i,
                    signature=stripped,
                    docstring=None,
                    is_exported="export" in stripped,
                ))

        # Import statements
        elif stripped.startswith("import ") or stripped.startswith("const ") and "require(" in stripped:
            pass

    return ParsedFile(
        path=file_info["path"],
        name=file_info["name"],
        extension=file_info["extension"],
        language=language,
        line_count=file_info["line_count"],
        size_bytes=file_info["size_bytes"],
        symbols=symbols,
        relationships=relationships,
    )


async def save_parsed_data(
    db: AsyncSession,
    repository: Repository,
    parsed_files: List[ParsedFile],
):
    """Save parsed files, symbols, and relationships to database."""
    # Create files
    file_map = {}
    for pf in parsed_files:
        file_obj = File(
            repository_id=repository.id,
            path=pf.path,
            name=pf.name,
            extension=pf.extension,
            language=pf.language,
            line_count=pf.line_count,
            size_bytes=pf.size_bytes,
            complexity_score=pf.complexity_score,
            is_entry_point=pf.is_entry_point,
            is_test_file=pf.is_test_file,
        )
        db.add(file_obj)
        await db.flush()
        file_map[pf.path] = file_obj.id

    # Create symbols
    symbol_map = {}
    for pf in parsed_files:
        file_id = file_map.get(pf.path)
        if not file_id:
            continue

        for ps in pf.symbols:
            symbol = Symbol(
                file_id=file_id,
                repository_id=repository.id,
                name=ps.name,
                qualified_name=ps.qualified_name,
                symbol_type=ps.symbol_type,
                start_line=ps.start_line,
                end_line=ps.end_line,
                signature=ps.signature,
                docstring=ps.docstring,
                is_exported=ps.is_exported,
                metadata=ps.metadata,
            )
            db.add(symbol)
            await db.flush()
            symbol_map[ps.qualified_name] = symbol.id

    # Create relationships
    for pf in parsed_files:
        for pr in pf.relationships:
            source_id = symbol_map.get(pr.source_qualified_name)
            target_id = symbol_map.get(pr.target_qualified_name)

            if source_id and target_id:
                rel = Relationship(
                    repository_id=repository.id,
                    source_symbol_id=source_id,
                    target_symbol_id=target_id,
                    relationship_type=pr.relationship_type,
                    line_number=pr.line_number,
                    is_dynamic=pr.is_dynamic,
                )
                db.add(rel)

    await db.commit()


# Add missing import
from datetime import datetime
from uuid import UUID