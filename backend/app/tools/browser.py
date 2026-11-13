import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.config import settings
from app.permissions.policy import ActionTier
from app.tools.registry import BaseTool, VerificationResult

logger = logging.getLogger("reeta.browser")


async def _launch_browser(playwright_instance, headless: bool = True):
    """Launches Microsoft Edge on Windows if available, falling back to bundled chromium."""
    channel = getattr(settings, "BROWSER_CHANNEL", "msedge")
    if channel:
        try:
            return await playwright_instance.chromium.launch(
                channel=channel,
                headless=headless,
            )
        except Exception as e:
            logger.info(f"Could not launch browser with channel '{channel}': {e}. Falling back to default chromium.")
    return await playwright_instance.chromium.launch(headless=headless)


class BrowserNavigateInput(BaseModel):
    url: str = Field(..., description="Web URL to navigate to (e.g. 'https://en.wikipedia.org')")
    headless: Optional[bool] = Field(default=True, description="Whether to run browser headlessly")


class BrowserNavigateTool(BaseTool):
    name = "browser_navigate"
    description = "Navigates to a website using Playwright Chromium, extracts page title, content, and captures a screenshot."
    category = "browser"
    args_schema = BrowserNavigateInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 45.0

    async def execute(self, url: str, headless: Optional[bool] = True) -> Dict[str, Any]:
        from playwright.async_api import async_playwright

        screenshots_dir = Path(settings.AUTHORIZED_WORKSPACE) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        shot_path = screenshots_dir / f"web_{int(time.time())}.png"

        async with async_playwright() as p:
            browser = await _launch_browser(
                p,
                headless=(settings.PLAYWRIGHT_HEADLESS if headless is None else headless),
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 REETA/1.0",
            )
            page = await context.new_page()

            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                status_code = response.status if response else 200
                title = await page.title()

                # Extract cleaned text
                body_text = await page.inner_text("body")
                cleaned_text = " ".join(body_text.split())[:10000]

                # Take screenshot
                await page.screenshot(path=str(shot_path))

            finally:
                await browser.close()

        # Wrap external content in untrusted delimiter to prevent prompt injection
        safe_content = f"<untrusted_web_data source='{url}'>\n{cleaned_text}\n</untrusted_web_data>"

        return {
            "url": url,
            "status_code": status_code,
            "title": title,
            "content": safe_content,
            "content_length": len(cleaned_text),
            "screenshot_path": str(shot_path),
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and result.get("title"):
            shot = Path(result.get("screenshot_path", ""))
            has_shot = shot.exists() and shot.stat().st_size > 0
            return VerificationResult(
                verified=True,
                evidence=f"Successfully loaded '{result.get('url')}' (Title: '{result.get('title')}', Status: {result.get('status_code')}, Screenshot: {has_shot}).",
            )
        return VerificationResult(verified=False, evidence="Browser navigation did not retrieve a valid page.")


class BrowserExtractInput(BaseModel):
    url: str = Field(..., description="Target webpage URL to scrape structured tables and headings from.")


class BrowserExtractTool(BaseTool):
    name = "browser_extract_tables"
    description = "Extracts structured tabular data from a webpage using Playwright."
    category = "browser"
    args_schema = BrowserExtractInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 45.0

    async def execute(self, url: str) -> Dict[str, Any]:
        from playwright.async_api import async_playwright
        from bs4 import BeautifulSoup

        async with async_playwright() as p:
            browser = await _launch_browser(p, headless=True)
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                html = await page.content()
            finally:
                await browser.close()

        soup = BeautifulSoup(html, "html.parser")
        tables_data = []

        for table in soup.find_all("table")[:5]:
            rows = []
            for tr in table.find_all("tr"):
                cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cols:
                    rows.append(cols)
            if rows:
                tables_data.append(rows)

        return {
            "url": url,
            "tables_extracted": len(tables_data),
            "data": tables_data,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and "tables_extracted" in result:
            return VerificationResult(
                verified=True,
                evidence=f"Extracted {result['tables_extracted']} tables from {result.get('url')}.",
            )
        return VerificationResult(verified=False, evidence="Table extraction failed.")



# ============================================================================
# 3. Browser Search Tool (YouTube / Search Engine via Edge)
# ============================================================================

class BrowserSearchInput(BaseModel):
    query: str = Field(..., description="Search query string (e.g. 'lo-fi music', 'latest windows updates')")
    site: Optional[str] = Field(default="google", description="Target site: 'google', 'youtube', 'bing', or 'wikipedia'")
    headless: Optional[bool] = Field(default=True, description="Whether to run browser headlessly")


class BrowserSearchTool(BaseTool):
    name = "browser_search"
    description = "Searches for content on YouTube, Google, or Bing using Microsoft Edge via Playwright."
    category = "browser"
    args_schema = BrowserSearchInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 45.0

    async def execute(self, query: str, site: str = "google", headless: Optional[bool] = True) -> Dict[str, Any]:
        from playwright.async_api import async_playwright
        import urllib.parse

        encoded_q = urllib.parse.quote_plus(query.strip())
        if "youtube" in site.lower() or "youtube" in query.lower():
            target_url = f"https://www.youtube.com/results?search_query={encoded_q}"
        elif "bing" in site.lower():
            target_url = f"https://www.bing.com/search?q={encoded_q}"
        elif "wikipedia" in site.lower():
            target_url = f"https://en.wikipedia.org/w/index.php?search={encoded_q}"
        else:
            target_url = f"https://www.google.com/search?q={encoded_q}"

        screenshots_dir = Path(settings.AUTHORIZED_WORKSPACE) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        shot_path = screenshots_dir / f"search_{int(time.time())}.png"

        async with async_playwright() as p:
            browser = await _launch_browser(p, headless=(settings.PLAYWRIGHT_HEADLESS if headless is None else headless))
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()

            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(1.5)
                title = await page.title()
                await page.screenshot(path=str(shot_path))
                body_text = await page.inner_text("body")
                results_text = " ".join(body_text.split())[:4000]
            finally:
                await browser.close()

        safe_content = f"<untrusted_web_data query='{query}' url='{target_url}'>\n{results_text}\n</untrusted_web_data>"

        return {
            "query": query,
            "target_url": target_url,
            "title": title,
            "screenshot_path": str(shot_path),
            "snippet": safe_content,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and result.get("target_url"):
            return VerificationResult(
                verified=True,
                evidence=f"Navigated to '{result.get('target_url')}' and retrieved search results (Page title: '{result.get('title')}').",
            )
        return VerificationResult(verified=False, evidence="Browser search failed.")


# ============================================================================
# 4. Browser Download Tool
# ============================================================================

class BrowserDownloadInput(BaseModel):
    url: str = Field(..., description="Direct file URL to download via browser/HTTP.")
    save_as: Optional[str] = Field(default=None, description="Optional target filename in authorized workspace.")


class BrowserDownloadTool(BaseTool):
    name = "browser_download"
    description = "Downloads a file from a URL into the authorized workspace."
    category = "browser"
    args_schema = BrowserDownloadInput
    default_tier = ActionTier.AUTONOMOUS
    timeout_seconds = 60.0

    async def execute(self, url: str, save_as: Optional[str] = None) -> Dict[str, Any]:
        import httpx
        from urllib.parse import urlparse

        workspace = Path(settings.AUTHORIZED_WORKSPACE) / "Downloads"
        workspace.mkdir(parents=True, exist_ok=True)

        if not save_as:
            parsed = urlparse(url)
            filename = Path(parsed.path).name or f"download_{int(time.time())}.bin"
        else:
            filename = Path(save_as).name

        target_file = workspace / filename

        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(target_file, "wb") as f:
                f.write(resp.content)

        return {
            "url": url,
            "saved_to": str(target_file),
            "filename": filename,
            "size_bytes": target_file.stat().st_size,
        }

    async def verify_outcome(self, result: Any, **kwargs) -> VerificationResult:
        if isinstance(result, dict) and result.get("saved_to"):
            p = Path(result["saved_to"])
            if p.exists() and p.stat().st_size > 0:
                return VerificationResult(
                    verified=True,
                    evidence=f"Empirically verified downloaded file exists at {p} ({p.stat().st_size} bytes).",
                )
        return VerificationResult(verified=False, evidence="Download verification failed.")
