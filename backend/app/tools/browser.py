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
            browser = await p.chromium.launch(
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
            browser = await p.chromium.launch(headless=True)
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
