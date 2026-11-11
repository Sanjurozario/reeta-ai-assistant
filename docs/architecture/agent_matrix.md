# REETA Agent Responsibility Matrix & Tool Contracts

This document defines the specialized agent hierarchy, boundaries, shared tool contracts, input/output schemas, and verification requirements for REETA.

---

## 1. Master Agent Topology

```
+-----------------------------------------------------------------------------------+
|                        CENTRAL ORCHESTRATOR (LangGraph)                           |
|  - Goal Decomposer        - Dependency Graph Planner     - Step Router            |
|  - Shared State Manager   - Verification Gatekeeper      - Context Aggregator     |
+-----------------------------------------------------------------------------------+
        |                 |                  |                 |               |
        v                 v                  v                 v               v
+---------------+ +----------------+ +----------------+ +---------------+ +--------------------+
|Research Agent | |  Coding Agent  | | Computer Agent | | Browser Agent | |     File Agent     |
| - Web Search  | | - AST & Index  | | - pywinauto    | | - Playwright  | | - Pathlib / Shutil |
| - Extraction  | | - Edit & Patch | | - PyAutoGUI    | | - Navigation  | | - Office / PDF     |
| - Verification| | - Test Runner  | | - Vision & OCR | | - Form Fill   | | - Clean & Organize |
+---------------+ +----------------+ +----------------+ +---------------+ +--------------------+
                                             |
                                             v
                                  +--------------------+
                                  | Productivity Agent |
                                  | - Reminders & Cron |
                                  | - Scheduler        |
                                  | - Integrations     |
                                  +--------------------+
```

---

## 2. Agent Specifications & Contracts

### 2.1 Central Orchestrator
- **Role:** Meta-planner and execution conductor.
- **Responsibilities:**
  - Ingests natural-language user objectives from Voice or Text.
  - Queries Cognitive Memory to retrieve user preferences, active project context, and past solutions.
  - Generates a Directed Acyclic Graph (DAG) plan with explicit dependencies.
  - Dynamically dispatches sub-tasks to the single best-suited specialized agent.
  - Monitors execution status and checkpoints graph state.
  - Enforces human-in-the-loop approvals for Tier 2 operations.
  - Coordinates verification before closing a task.
- **Constraints:** Never invokes host operating system tools directly; strictly delegates to specialized workers.

---

### 2.2 Research Agent
- **Role:** Deep information gathering, web investigation, and structured report synthesis.
- **Assigned Tools:**
  - `web_search(query: str, num_results: int) -> List[SearchResult]`
  - `fetch_web_page(url: str, extract_format: 'markdown' | 'text') -> str`
  - `fact_check_claim(claim: str, sources: List[str]) -> FactCheckResult`
  - `generate_report(title: str, content: str, format: 'pdf' | 'markdown') -> str`
- **Default Autonomy Tier:** Tier 1 (Autonomous).
- **Verification Strategy:** Asserts that every fact in generated reports cites a retrieved source URL; verifies HTTP 200 response and content non-emptiness for crawled URLs.
- **Output Contract:**
  ```typescript
  interface ResearchOutput {
    summary: string;
    findings: Array<{ topic: string; details: string; sources: string[] }>;
    unresolved_questions: string[];
    generated_report_path?: string;
  }
  ```

---

### 2.3 Coding Agent
- **Role:** Software development, debugging, codebase navigation, refactoring, and automated testing.
- **Assigned Tools:**
  - `search_codebase(query: str, file_pattern: str) -> List[Match]`
  - `read_code_file(path: str, start_line?: int, end_line?: int) -> str`
  - `apply_code_patch(path: str, diff: str) -> PatchResult`
  - `create_file(path: str, content: str) -> bool`
  - `run_sandboxed_test(command: str, timeout_sec: int) -> TestRunResult`
  - `git_operation(subcommand: str, args: List[str]) -> str`
- **Default Autonomy Tier:** Tier 1 inside isolated Docker sandbox; Tier 2 for host file system modifications outside target project workspace.
- **Verification Strategy:** Runs unit tests (`pytest`, `npm test`, `cargo test`) within a Docker container. Evaluates exit code (0), parses test failure output, and checks syntax validity before reporting completion.
- **Output Contract:**
  ```typescript
  interface CodingOutput {
    files_modified: string[];
    files_created: string[];
    test_run: { total: number; passed: number; failed: number; output: string };
    explanation: string;
  }
  ```

---

### 2.4 Computer Agent (Windows Automation)
- **Role:** Direct Windows 11 GUI automation, window management, accessibility tree interaction, and visual desktop assistance.
- **Assigned Tools:**
  - `list_open_windows() -> List[WindowInfo]`
  - `focus_window(title_or_handle: str) -> bool`
  - `click_element(window: str, control_type: str, name: str) -> bool` (pywinauto UIA)
  - `type_text(window: str, text: str, control_name?: str) -> bool`
  - `capture_screen(bounding_box?: Rect) -> str` (returns Base64/path)
  - `analyze_screen_region(image_path: str, prompt: str) -> VisionAnalysis`
  - `coordinate_click(x: int, y: int, button: 'left' | 'right' | 'double') -> bool`
- **Default Autonomy Tier:** Tier 1 for inspection (`list_open_windows`, `capture_screen`); Tier 2 for clicking buttons that save/modify files or launch applications.
- **Verification Strategy:** Captures a post-action screenshot and inspects the UIA control tree to verify window state changes (e.g. asserting a dialog closed, a window opened, or a checkbox toggled).
- **Output Contract:**
  ```typescript
  interface ComputerOutput {
    action_performed: string;
    target_window: string;
    verified_state_change: boolean;
    post_action_screenshot?: string;
  }
  ```

---

### 2.5 Browser Agent
- **Role:** Deep web browsing, authenticated session handling, dynamic Single-Page Application (SPA) interaction, form submission, and web scraping.
- **Assigned Tools:**
  - `browser_navigate(url: str) -> PageState`
  - `browser_click(selector: str) -> bool`
  - `browser_type(selector: str, text: str) -> bool`
  - `browser_extract_table(selector: str) -> List[Dict[str, Any]]`
  - `browser_take_snapshot(full_page: bool) -> str`
  - `browser_download_file(url: str, destination: str) -> str`
- **Default Autonomy Tier:** Tier 1 for public informational navigation; Tier 2 for purchase buttons, financial forms, or sending external emails.
- **Verification Strategy:** Asserts DOM state transitions (e.g. element visibility, URL change, success notification banner presence).
- **Output Contract:**
  ```typescript
  interface BrowserOutput {
    current_url: string;
    page_title: string;
    data_extracted: any;
    screenshot_path?: string;
  }
  ```

---

### 2.6 File Agent
- **Role:** Host file operations, disk cleanup, batch reorganization, and document format processing (Markdown, PDF, DOCX, XLSX).
- **Assigned Tools:**
  - `search_files(pattern: str, root_dir: str) -> List[FileInfo]`
  - `read_file_content(path: str, max_bytes?: int) -> str`
  - `write_file_content(path: str, content: str) -> bool`
  - `copy_or_move(source: str, dest: str, operation: 'copy' | 'move') -> bool`
  - `batch_organize_folder(folder: str, rules: Dict[str, str]) -> BatchResult`
  - `convert_document(source: str, target_format: str) -> str`
- **Default Autonomy Tier:** Tier 1 for read/search within designated workspaces; Tier 2 for file deletion, mass move, or overwriting existing files.
- **Verification Strategy:** Asserts file existence on disk using `pathlib.Path.exists()`, validates non-zero file byte size, and compares MD5/SHA256 checksums.
- **Output Contract:**
  ```typescript
  interface FileOutput {
    operations_performed: Array<{ source: string; destination?: string; status: string }>;
    bytes_affected: number;
    verified_on_disk: boolean;
  }
  ```

---

### 2.7 Productivity Agent
- **Role:** Managing reminders, scheduling background automations, interacting with local calendar/tasks, and polling cron triggers.
- **Assigned Tools:**
  - `create_reminder(title: str, due_time: str, notify_channel: 'ui' | 'voice') -> str`
  - `list_scheduled_jobs() -> List[JobInfo]`
  - `schedule_cron_task(cron_expr: str, prompt: str) -> str`
  - `cancel_scheduled_job(job_id: str) -> bool`
- **Default Autonomy Tier:** Tier 1 for setting personal reminders; Tier 2 for recurring background scripts that execute terminal commands.
- **Verification Strategy:** Asserts database row creation in `scheduled_jobs` and validates next trigger calculation with Python `croniter`.
- **Output Contract:**
  ```typescript
  interface ProductivityOutput {
    job_id: string;
    next_run_timestamp: string;
    status: 'scheduled' | 'executed' | 'cancelled';
  }
  ```
