"""REETA Central Tool Registry initialization."""
from app.tools.registry import tool_registry, BaseTool, ToolExecutionResult, VerificationResult
from app.tools.files import FileSearchTool, FileReadTool, FileWriteTool, FileOrganizeTool
from app.tools.documents import PdfReportTool
from app.tools.terminal import PowerShellTool
from app.tools.windows import ListWindowsTool, OpenApplicationTool, CaptureScreenTool, KeyboardTypeTool
from app.tools.browser import BrowserNavigateTool, BrowserExtractTool
from app.tools.research import WebSearchTool
from app.tools.coding import CodeSearchTool, CodePatchTool, RunTestsTool
from app.tools.productivity import CreateReminderTool

# Register all concrete tools into global registry
_all_tools = [
    FileSearchTool(),
    FileReadTool(),
    FileWriteTool(),
    FileOrganizeTool(),
    PdfReportTool(),
    PowerShellTool(),
    ListWindowsTool(),
    OpenApplicationTool(),
    CaptureScreenTool(),
    KeyboardTypeTool(),
    BrowserNavigateTool(),
    BrowserExtractTool(),
    WebSearchTool(),
    CodeSearchTool(),
    CodePatchTool(),
    RunTestsTool(),
    CreateReminderTool(),
]

for tool in _all_tools:
    tool_registry.register_tool(tool)

__all__ = [
    "tool_registry",
    "BaseTool",
    "ToolExecutionResult",
    "VerificationResult",
]
