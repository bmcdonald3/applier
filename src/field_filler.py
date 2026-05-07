"""
Field filler: Execute DOM mutations to populate form fields.
"""

import time
import random
import json
from typing import Any, Dict, Optional
from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from .config import FIELD_FILL_DELAY_MIN, FIELD_FILL_DELAY_MAX
from .logger import logger


class FieldFiller:
    """Populate form fields using Playwright."""

    def __init__(self):
        self.delay_min = FIELD_FILL_DELAY_MIN
        self.delay_max = FIELD_FILL_DELAY_MAX

    def _add_delay(self):
        """Add random delay between field fills to simulate human typing."""
        delay = random.uniform(self.delay_min / 1000, self.delay_max / 1000)
        time.sleep(delay)

    def fill_field(self, page: Page, field_id: str, field_type: str, value: Any) -> Dict[str, Any]:
        """
        Fill a form field based on its type.

        Args:
            page: Playwright page object
            field_id: Field identifier
            field_type: Type of field (text, email, select, checkbox, etc.)
            value: Value to fill

        Returns:
            Dict with success status and any error message
        """
        try:
            self._add_delay()

            if field_type == "select":
                self._select_option(page, field_id, value)
            elif field_type in ("checkbox", "radio"):
                self._check_field(page, field_id, value)
            elif field_type == "file":
                self._upload_file(page, field_id, value)
            elif field_type == "date":
                self._fill_date(page, field_id, value)
            elif field_type == "rich-text":
                self._fill_rich_text(page, field_id, value)
            elif field_type == "textarea":
                self._fill_textarea(page, field_id, value)
            else:
                # Default: text input
                self._fill_text(page, field_id, value)

            logger.field_filled(field_id, "SUCCESS")
            return {"success": True, "fieldId": field_id}

        except Exception as e:
            error_msg = str(e)
            logger.field_filled(field_id, "FAILURE", error=error_msg)
            return {"success": False, "fieldId": field_id, "error": error_msg}

    def _fill_text(self, page: Page, field_id: str, value: str) -> None:
        """Fill text input field."""
        selector = self._build_selector(field_id)
        page.fill(selector, str(value))

    def _fill_textarea(self, page: Page, field_id: str, value: str) -> None:
        """Fill textarea field."""
        selector = self._build_selector(field_id)
        page.fill(selector, str(value))

    def _select_option(self, page: Page, field_id: str, value: Any) -> None:
        """Select an option from a dropdown."""
        selector = self._build_selector(field_id)
        
        # First try to select by value
        try:
            page.select_option(selector, str(value))
        except PlaywrightTimeoutError:
            # If that fails, try to find by visible text
            option_selector = f'{selector} >> text="{value}"'
            page.click(option_selector)

    def _check_field(self, page: Page, field_id: str, value: Any) -> None:
        """Check/uncheck a checkbox or select a radio button."""
        selector = self._build_selector(field_id)
        
        # Convert value to boolean
        should_check = self._to_bool(value)
        
        # For checkboxes, just check/uncheck
        if should_check:
            page.check(selector)
        else:
            page.uncheck(selector)

    def _upload_file(self, page: Page, field_id: str, file_path: str) -> None:
        """Upload a file."""
        selector = self._build_selector(field_id)
        
        # Validate file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Use Playwright's set_input_files
        page.set_input_files(selector, file_path)

    def _fill_date(self, page: Page, field_id: str, value: str) -> None:
        """Fill a date field."""
        selector = self._build_selector(field_id)
        
        # Try to determine date format from field attributes
        element = page.query_selector(selector)
        if element:
            placeholder = element.get_attribute("placeholder") or ""
            # For now, just fill the value directly
            page.fill(selector, value)
        else:
            page.fill(selector, value)

    def _fill_rich_text(self, page: Page, field_id: str, value: str) -> None:
        """Fill a contenteditable rich text editor."""
        selector = self._build_selector(field_id)
        
        # Clear existing content
        page.evaluate(f"""
            document.querySelector('{selector}').innerHTML = '';
        """)
        
        # Fill with new content
        page.evaluate(f"""
            const element = document.querySelector('{selector}');
            element.textContent = {json.dumps(value)};
            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
        """)

    @staticmethod
    def _build_selector(field_id: str) -> str:
        """Build a Playwright selector from field ID."""
        # Try multiple selector strategies
        # This will be improved if we encounter selector issues
        return f'[id="{field_id}"], [name="{field_id}"]'

    @staticmethod
    def _to_bool(value: Any) -> bool:
        """Convert value to boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1", "on")
        return bool(value)


# Create a singleton instance
field_filler = FieldFiller()
