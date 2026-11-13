"""REETA Central Tool Registry initialization."""
from app.tools.registry import tool_registry, BaseTool, ToolExecutionResult, VerificationResult
from app.tools.files import (
    FileSearchTool,
    FileReadTool,
    FileWriteTool,
    FileOrganizeTool,
    CreateDirectoryTool,
    DeleteFileTool,
    MoveFileTool,
    CopyFileTool,
    RenameFileTool,
)
from app.tools.documents import PdfReportTool
from app.tools.terminal import PowerShellTool
from app.tools.windows import (
    ListWindowsTool,
    OpenApplicationTool,
    CloseApplicationTool,
    FocusWindowTool,
    CaptureScreenTool,
    ReadScreenTool,
    KeyboardTypeTool,
    KeyboardHotkeyTool,
    MouseClickTool,
    SystemInfoTool,
    SetVolumeTool,
)
from app.tools.clipboard import ClipboardReadTool, ClipboardWriteTool
from app.tools.browser import (
    BrowserNavigateTool,
    BrowserExtractTool,
    BrowserSearchTool,
    BrowserDownloadTool,
)
from app.tools.research import WebSearchTool
from app.tools.coding import CodeSearchTool, CodePatchTool, RunTestsTool, RunScriptTool
from app.tools.productivity import CreateReminderTool, StartTimerTool, ManageNotesTool
from app.tools.memory_tools import MemoryStoreTool, MemorySearchTool, MemoryForgetTool

# Register all concrete tools into global registry
_all_tools = [
    # Files
    FileSearchTool(),
    FileReadTool(),
    FileWriteTool(),
    FileOrganizeTool(),
    CreateDirectoryTool(),
    DeleteFileTool(),
    MoveFileTool(),
    CopyFileTool(),
    RenameFileTool(),
    # Documents & Shell
    PdfReportTool(),
    PowerShellTool(),
    # Windows Desktop & System
    ListWindowsTool(),
    OpenApplicationTool(),
    CloseApplicationTool(),
    FocusWindowTool(),
    CaptureScreenTool(),
    ReadScreenTool(),
    KeyboardTypeTool(),
    KeyboardHotkeyTool(),
    MouseClickTool(),
    SystemInfoTool(),
    SetVolumeTool(),
    # Clipboard
    ClipboardReadTool(),
    ClipboardWriteTool(),
    # Browser
    BrowserNavigateTool(),
    BrowserExtractTool(),
    BrowserSearchTool(),
    BrowserDownloadTool(),
    # Research
    WebSearchTool(),
    # Coding
    CodeSearchTool(),
    CodePatchTool(),
    RunTestsTool(),
    RunScriptTool(),
    # Productivity
    CreateReminderTool(),
    StartTimerTool(),
    ManageNotesTool(),
    # Memory
    MemoryStoreTool(),
    MemorySearchTool(),
    MemoryForgetTool(),
]

for tool in _all_tools:
    tool_registry.register_tool(tool)

__all__ = [
    "tool_registry",
    "BaseTool",
    "ToolExecutionResult",
    "VerificationResult",
]
