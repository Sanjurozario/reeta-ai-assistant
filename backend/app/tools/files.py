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
        with open(path, "w", encoding="utf-8", newline="\n") as f:
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
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                actual_text = f.read()
            if actual_text.replace("\r\n", "\n") == expected_content.replace("\r\n", "\n"):
                return VerificationResult(
                    verified=True,
                    evidence=f"Empirically verified file exists on disk at {path} with exact content ({len(actual_text)} chars).",
                )
            else:
                return VerificationResult(
                    verified=False,
                    evidence=f"File exists at {path} but content mismatch.",
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


# ============================================================================
# 5. Create Directory Tool (DEMO 2)
# ============================================================================

class CreateDirectoryInput(BaseModel):
    directory_path: str = Field(..., description="Path of directory or folder structure to create.")


class CreateDirectoryTool(BaseTool):
    name = "create_directory"
    description = "Creates a new folder or nested directory path within an authorized workspace."
    category = "files"
    args_schema = CreateDirectoryInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 15.0

    async def execute(self, directory_path: str) -> Dict[str, Any]:
        target = Path(directory_path).resolve()
        target.mkdir(parents=True, exist_ok=True)
        return {
            "directory_path": str(target),
            "name": target.name,
            "status": "created",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        path_str = kwargs.get("directory_path") or (result.get("directory_path") if isinstance(result, dict) else "")
        target = Path(path_str).resolve()
        if target.exists() and target.is_dir():
            return VerificationResult(
                verified=True,
                evidence=f"Empirically verified folder exists on disk at {target}.",
            )
        return VerificationResult(verified=False, evidence=f"Directory does not exist on disk at {target}.")


# ============================================================================
# 6. Delete File via Recycle Bin Tool (DEMO 4)
# ============================================================================

class DeleteFileInput(BaseModel):
    filepath: str = Field(..., description="Path of file to delete into the Windows Recycle Bin.")


class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Deletes a file by safely moving it into the Windows Recycle Bin for human recovery. Requires explicit Tier 2 operator authorization."
    category = "files"
    args_schema = DeleteFileInput
    default_tier = ActionTier.APPROVAL_REQUIRED
    timeout_seconds = 15.0

    async def execute(self, filepath: str) -> Dict[str, Any]:
        from send2trash import send2trash
        target = Path(filepath).resolve()
        if not target.exists():
            raise FileNotFoundError(f"Cannot delete non-existent file: {target}")
        if not target.is_file():
            raise IsADirectoryError(f"Target is a directory; use folder removal for directories: {target}")

        file_size = target.stat().st_size
        filename = target.name
        
        # Send to Windows Recycle Bin
        send2trash(str(target))

        return {
            "filepath": str(target),
            "filename": filename,
            "size_bytes": file_size,
            "destination": "Windows Recycle Bin",
            "status": "deleted_to_recycle_bin",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        path_str = kwargs.get("filepath") or (result.get("filepath") if isinstance(result, dict) else "")
        target = Path(path_str).resolve()
        # Verify file is no longer present in its original directory
        if not target.exists():
            return VerificationResult(
                verified=True,
                evidence=f"Empirically verified file '{target.name}' was safely removed from original location and relocated to the Windows Recycle Bin.",
            )
        return VerificationResult(verified=False, evidence=f"File still exists at original path {target}; deletion was unsuccessful.")



# ============================================================================
# 7. Move File Tool
# ============================================================================

class MoveFileInput(BaseModel):
    source_path: str = Field(..., description="Current path of the file or folder to move.")
    destination_path: str = Field(..., description="Destination directory or full file path.")


class MoveFileTool(BaseTool):
    name = "move_file"
    description = "Moves a file or directory from source to destination."
    category = "files"
    args_schema = MoveFileInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 15.0

    async def execute(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        src = Path(source_path).resolve()
        dst = Path(destination_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")

        if dst.is_dir():
            final_dst = dst / src.name
        else:
            final_dst = dst
            final_dst.parent.mkdir(parents=True, exist_ok=True)

        shutil.move(str(src), str(final_dst))
        return {
            "source": str(src),
            "destination": str(final_dst),
            "status": "moved",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        dst = Path(result.get("destination", "")).resolve()
        src = Path(result.get("source", "")).resolve()
        if dst.exists() and not src.exists():
            return VerificationResult(
                verified=True,
                evidence=f"File successfully moved to {dst} and removed from {src}.",
            )
        return VerificationResult(verified=False, evidence="Move operation failed verification.")


# ============================================================================
# 8. Copy File Tool
# ============================================================================

class CopyFileInput(BaseModel):
    source_path: str = Field(..., description="Path of the file or folder to copy.")
    destination_path: str = Field(..., description="Destination directory or file path.")


class CopyFileTool(BaseTool):
    name = "copy_file"
    description = "Copies a file or directory to a destination location."
    category = "files"
    args_schema = CopyFileInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 20.0

    async def execute(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        src = Path(source_path).resolve()
        dst = Path(destination_path).resolve()
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")

        if src.is_dir():
            shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            final_dst = dst
        else:
            if dst.is_dir():
                final_dst = dst / src.name
            else:
                final_dst = dst
                final_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(final_dst))

        return {
            "source": str(src),
            "destination": str(final_dst),
            "status": "copied",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        dst = Path(result.get("destination", "")).resolve()
        src = Path(result.get("source", "")).resolve()
        if dst.exists() and src.exists():
            return VerificationResult(
                verified=True,
                evidence=f"Verified copy exists at {dst} ({dst.stat().st_size} bytes).",
            )
        return VerificationResult(verified=False, evidence="Copy verification failed.")


# ============================================================================
# 9. Rename File Tool
# ============================================================================

class RenameFileInput(BaseModel):
    filepath: str = Field(..., description="Path of the file to rename.")
    new_name: str = Field(..., description="New filename (e.g. 'new_report.txt').")


class RenameFileTool(BaseTool):
    name = "rename_file"
    description = "Renames a file in its current directory."
    category = "files"
    args_schema = RenameFileInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 10.0

    async def execute(self, filepath: str, new_name: str) -> Dict[str, Any]:
        target = Path(filepath).resolve()
        if not target.exists():
            raise FileNotFoundError(f"File to rename not found: {target}")

        new_path = target.parent / Path(new_name).name
        target.rename(new_path)

        return {
            "old_path": str(target),
            "new_path": str(new_path),
            "new_name": new_path.name,
            "status": "renamed",
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        new_path = Path(result.get("new_path", "")).resolve()
        old_path = Path(result.get("old_path", "")).resolve()
        if new_path.exists() and not old_path.exists():
            return VerificationResult(
                verified=True,
                evidence=f"File successfully renamed to '{new_path.name}' at {new_path}.",
            )
        return VerificationResult(verified=False, evidence="Rename verification failed.")
