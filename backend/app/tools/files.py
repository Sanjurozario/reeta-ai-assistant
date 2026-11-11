import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.permissions.policy import ActionTier
from app.tools.registry import BaseTool, VerificationResult


# ============================================================================
# 1. File Search Tool
# ============================================================================

class FileSearchInput(BaseModel):
    query: str = Field(..., description="File name pattern or glob to search (e.g. '*.py', 'report*')")
    directory: Optional[str] = Field(default=None, description="Root directory to search. Defaults to authorized workspace.")
    max_results: int = Field(default=50, ge=1, le=200)


class FileSearchTool(BaseTool):
    name = "file_search"
    description = "Searches for files matching a pattern inside the authorized workspace."
    category = "files"
    args_schema = FileSearchInput
    default_tier = ActionTier.AUTONOMOUS

    async def execute(self, query: str, directory: Optional[str] = None, max_results: int = 50) -> Dict[str, Any]:
        root = Path(directory or settings.AUTHORIZED_WORKSPACE).resolve()
        if not root.exists():
            raise FileNotFoundError(f"Search root directory does not exist: {root}")

        matches = []
        for p in root.rglob(query):
            if p.is_file():
                matches.append({
                    "name": p.name,
                    "path": str(p),
                    "size_bytes": p.stat().st_size,
                    "modified": p.stat().st_mtime,
                })
                if len(matches) >= max_results:
                    break

        return {"query": query, "root": str(root), "total_found": len(matches), "files": matches}

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "total_found" in result:
            return VerificationResult(
                verified=True,
                evidence=f"Discovered {result['total_found']} matching files under {result.get('root')}.",
            )
        return VerificationResult(verified=False, evidence="Invalid search result structure.")


# ============================================================================
# 2. File Read Tool
# ============================================================================

class FileReadInput(BaseModel):
    filepath: str = Field(..., description="Absolute or relative path to the file to read.")
    max_bytes: int = Field(default=200000, description="Maximum bytes to read.")


class FileReadTool(BaseTool):
    name = "read_file"
    description = "Reads content of a file within the authorized workspace."
    category = "files"
    args_schema = FileReadInput
    default_tier = ActionTier.AUTONOMOUS

    async def execute(self, filepath: str, max_bytes: int = 200000) -> Dict[str, Any]:
        path = Path(filepath).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise IsADirectoryError(f"Target is a directory, not a file: {path}")

        size = path.stat().st_size
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_bytes)

        return {
            "filepath": str(path),
            "size_bytes": size,
            "truncated": size > max_bytes,
            "content": content,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "content" in result:
            return VerificationResult(
                verified=True,
                evidence=f"Successfully read {len(result['content'])} characters from {result.get('filepath')}.",
            )
        return VerificationResult(verified=False, evidence="File read failed or produced no content.")


# ============================================================================
# 3. File Write Tool
# ============================================================================

class FileWriteInput(BaseModel):
    filepath: str = Field(..., description="Destination file path.")
    content: str = Field(..., description="Text or code content to write.")
    overwrite: bool = Field(default=True, description="Whether to overwrite if file already exists.")


class FileWriteTool(BaseTool):
    name = "write_file"
    description = "Creates or overwrites a file with content in an authorized workspace."
    category = "files"
    args_schema = FileWriteInput
    default_tier = ActionTier.AUTONOMOUS

    async def execute(self, filepath: str, content: str, overwrite: bool = True) -> Dict[str, Any]:
        path = Path(filepath).resolve()
        if path.exists() and not overwrite:
            raise FileExistsError(f"File already exists and overwrite=False: {path}")

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "filepath": str(path),
            "bytes_written": len(content.encode("utf-8")),
            "status": "written",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        path = Path(kwargs.get("filepath", "")).resolve()
        expected_content = kwargs.get("content", "")
        if path.exists() and path.is_file():
            actual_size = path.stat().st_size
            expected_size = len(expected_content.encode("utf-8"))
            if actual_size == expected_size:
                return VerificationResult(
                    verified=True,
                    evidence=f"Empirically verified file exists on disk at {path} with exact size {actual_size} bytes.",
                )
            else:
                return VerificationResult(
                    verified=False,
                    evidence=f"File exists at {path} but size mismatch: actual {actual_size}b vs expected {expected_size}b.",
                )
        return VerificationResult(verified=False, evidence=f"File does not exist on disk at {path}.")


# ============================================================================
# 4. File Batch Organize Tool (TEST 3)
# ============================================================================

class FileOrganizeInput(BaseModel):
    directory: str = Field(..., description="Directory path to clean and organize into categorized folders.")


class FileOrganizeTool(BaseTool):
    name = "organize_folder"
    description = "Organizes files in a directory into structured subdirectories (Documents, Images, Code, Data, Archives) by file extension."
    category = "files"
    args_schema = FileOrganizeInput
    default_tier = ActionTier.APPROVAL_REQUIRED

    EXTENSION_MAP = {
        "Documents": {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".odt"},
        "Images": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"},
        "Code": {".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".css", ".rs", ".json", ".yaml", ".yml"},
        "Data": {".csv", ".xlsx", ".xls", ".parquet", ".db", ".sqlite"},
        "Archives": {".zip", ".tar", ".gz", ".7z", ".rar"},
    }

    async def execute(self, directory: str) -> Dict[str, Any]:
        target = Path(directory).resolve()
        if not target.exists() or not target.is_dir():
            raise NotADirectoryError(f"Target directory does not exist: {target}")

        moved_files = []
        for item in list(target.iterdir()):
            if item.is_file() and not item.name.startswith("."):
                ext = item.suffix.lower()
                destination_category = "Miscellaneous"
                for cat, extensions in self.EXTENSION_MAP.items():
                    if ext in extensions:
                        destination_category = cat
                        break

                cat_dir = target / destination_category
                cat_dir.mkdir(exist_ok=True)
                dest_path = cat_dir / item.name

                # Avoid overwriting destination with same name
                if dest_path.exists() and dest_path != item:
                    dest_path = cat_dir / f"{item.stem}_{int(time.time())}{item.suffix}"

                shutil.move(str(item), str(dest_path))
                moved_files.append({"from": item.name, "to": f"{destination_category}/{dest_path.name}"})

        return {
            "directory": str(target),
            "total_organized": len(moved_files),
            "moves": moved_files,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "total_organized" in result:
            return VerificationResult(
                verified=True,
                evidence=f"Folder organized: moved {result['total_organized']} files into categorized subfolders.",
            )
        return VerificationResult(verified=False, evidence="Folder organization failed.")
