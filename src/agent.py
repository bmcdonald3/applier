"""
Main agent orchestration: Automate job application filling.
"""

import sys
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from playwright.sync_api import sync_playwright
from .config import (
    PROFILE_FILE,
    BROWSER_HEADLESS,
    BROWSER_TIMEOUT,
    PAGE_WAIT_TIMEOUT,
    CHECKPOINT_INTERVAL,
    VALIDATION_RETRY_MAX,
    validate_config,
)
from .form_extractor import form_extractor
from .llm_mapper import llm_mapper
from .field_filler import field_filler
from .validation_handler import validation_handler
from .session_manager import session_manager
from .logger import logger


class ApplicationAgent:
    """Main orchestration agent for automated job applications."""

    def __init__(self):
        validate_config()
        self.profile = self._load_profile()
        self.browser = None
        self.page = None
        self.session = None
        self.form_schema = None
        self.mappings = None

    def _load_profile(self) -> Dict[str, Any]:
        """Load applicant profile from JSON file."""
        if not os.path.exists(PROFILE_FILE):
            raise FileNotFoundError(
                f"Profile file not found: {PROFILE_FILE}. "
                f"Copy profile.json.template to {PROFILE_FILE} and fill in your data."
            )

        try:
            with open(PROFILE_FILE, "r") as f:
                profile = json.load(f)
            logger.info("PROFILE_LOADED", f"Profile loaded from {PROFILE_FILE}")
            return profile
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {PROFILE_FILE}: {str(e)}")

    def run(self, url: str) -> bool:
        """
        Main application flow.

        Args:
            url: Job application URL

        Returns:
            True if submitted, False otherwise
        """
        try:
            # Check for existing session
            existing_session = session_manager.load_session()
            if existing_session and existing_session.get("url") == url:
                print(f"Resuming previous application for {url}")
                self.session = existing_session
            else:
                self.session = session_manager.create_session(url)
                print(f"Starting new application for {url}")

            # Initialize browser
            self._init_browser()

            # Navigate to URL
            self._navigate(url)

            # Extract form
            self._extract_form()

            # Get LLM mappings
            self._get_llm_mappings()

            # Fill fields
            self._fill_fields()

            # Manual review
            return self._manual_review()

        except Exception as e:
            logger.error("AGENT_RUN", f"Application failed: {str(e)}")
            print(f"Error: {str(e)}", file=sys.stderr)
            return False

        finally:
            self._cleanup()

    def _init_browser(self) -> None:
        """Initialize Playwright browser."""
        playwright = sync_playwright().start()
        self.browser = playwright.chromium.launch(headless=BROWSER_HEADLESS)
        self.page = self.browser.new_page()
        logger.info("BROWSER_INIT", "Browser initialized")

    def _navigate(self, url: str) -> None:
        """Navigate to application URL."""
        self.page.goto(url, timeout=BROWSER_TIMEOUT)
        self.page.wait_for_load_state("networkidle", timeout=PAGE_WAIT_TIMEOUT)
        logger.info("PAGE_NAVIGATED", f"Navigated to {url}")

    def _extract_form(self) -> None:
        """Extract form schema from page."""
        self.form_schema = form_extractor.extract_form_schema(self.page)
        field_count = len(self.form_schema.get("fields", []))
        logger.form_extracted(self.session["url"], field_count)
        print(f"Extracted {field_count} form fields")

    def _get_llm_mappings(self) -> None:
        """Get field mappings from LLM."""
        print("Analyzing form fields with AI...")
        self.mappings = llm_mapper.map_profile_to_form(self.profile, self.form_schema)

        # Log mappings
        for mapping in self.mappings.get("mappings", []):
            logger.field_mapped(
                mapping["fieldId"],
                mapping["fieldLabel"],
                mapping["mappedValue"],
                mapping["confidence"],
                mapping["requiresManualReview"],
            )

    def _fill_fields(self) -> None:
        """Fill form fields based on mappings."""
        checkpoint_count = 0
        failed_fields = []
        flagged_fields = []

        for i, mapping in enumerate(self.mappings.get("mappings", [])):
            field_id = mapping["fieldId"]
            field_label = mapping["fieldLabel"]
            mapped_value = mapping["mappedValue"]
            confidence = mapping["confidence"]
            requires_review = mapping["requiresManualReview"]

            # Skip null values
            if mapped_value is None:
                continue

            # Find field type
            field = next(
                (f for f in self.form_schema.get("fields", []) if f["fieldId"] == field_id),
                None,
            )
            if not field:
                continue

            field_type = field["fieldType"]

            # Determine action based on confidence
            if confidence >= 0.8:
                # Auto-fill
                print(f"  Filling: {field_label} (confidence: {confidence:.0%})")
                result = field_filler.fill_field(self.page, field_id, field_type, mapped_value)

                if not result["success"]:
                    # Try validation recovery
                    alternative = validation_handler.handle_validation_failure(
                        self.page,
                        field_id,
                        field_type,
                        mapped_value,
                        self.form_schema,
                        self.profile,
                        llm_mapper,
                    )

                    if alternative:
                        print(f"  Retrying with alternative value...")
                        result = field_filler.fill_field(self.page, field_id, field_type, alternative)

                    if not result["success"]:
                        failed_fields.append(field_id)

                if result["success"]:
                    self.session["filledFields"][field_id] = mapped_value

            else:
                # Flag for manual review
                flagged_fields.append(
                    {"fieldId": field_id, "fieldLabel": field_label, "suggestedValue": mapped_value, "confidence": confidence}
                )

            # Save checkpoint every N fields
            checkpoint_count += 1
            if checkpoint_count % CHECKPOINT_INTERVAL == 0:
                self.session["checkpointCount"] = checkpoint_count
                checkpoint_data = {
                    "url": self.session["url"],
                    "filledFieldCount": len(self.session["filledFields"]),
                    "failedFieldCount": len(failed_fields),
                    "filledFields": self.session["filledFields"],
                }
                session_manager.save_checkpoint(checkpoint_data)

        self.session["failedFields"] = failed_fields
        self.session["flaggedFields"] = flagged_fields
        session_manager.save_session(self.session)

        print(f"Filled {len(self.session['filledFields'])} fields")
        if failed_fields:
            print(f"Failed to fill {len(failed_fields)} fields: {failed_fields}")
        if flagged_fields:
            print(f"Flagged {len(flagged_fields)} fields for review")

    def _manual_review(self) -> bool:
        """Manual review phase before submission."""
        logger.manual_review_start(
            len(self.session["flaggedFields"]),
            len(self.session["failedFields"]),
        )

        print("\n" + "=" * 80)
        print("MANUAL REVIEW PHASE")
        print("=" * 80)

        # Show filled fields
        if self.session["filledFields"]:
            print("\n✓ Auto-filled fields:")
            for field_id, value in list(self.session["filledFields"].items())[:5]:
                print(f"  - {field_id}: {str(value)[:50]}")
            if len(self.session["filledFields"]) > 5:
                print(f"  ... and {len(self.session['filledFields']) - 5} more")

        # Show flagged fields
        if self.session["flaggedFields"]:
            print("\n⚠ Fields flagged for review (low confidence):")
            for flag in self.session["flaggedFields"]:
                print(
                    f"  - {flag['fieldLabel']}: suggested {flag['suggestedValue']} "
                    f"(confidence: {flag['confidence']:.0%})"
                )

        # Show failed fields
        if self.session["failedFields"]:
            print("\n✗ Fields that failed to fill:")
            for field_id in self.session["failedFields"]:
                print(f"  - {field_id}")

        print("\nPlease review the form in the browser window above.")
        print("Check flagged fields and fill in any that need correction.")
        print("\nWhen ready to proceed, enter your choice:")

        while True:
            choice = input("Submit application? (yes/no): ").strip().lower()
            if choice in ("yes", "y"):
                return self._submit()
            elif choice in ("no", "n"):
                logger.submission(False)
                print("Application cancelled.")
                return False
            else:
                print("Please enter 'yes' or 'no'")

    def _submit(self) -> bool:
        """Submit the form."""
        try:
            # Find and click submit button
            submit_button = self.page.query_selector('button[type="submit"], input[type="submit"]')
            if submit_button:
                submit_button.click()
                self.page.wait_for_load_state("networkidle", timeout=PAGE_WAIT_TIMEOUT)
                logger.submission(True)
                print("Form submitted successfully!")
                return True
            else:
                print("Could not find submit button")
                logger.submission(False, "Submit button not found")
                return False
        except Exception as e:
            logger.submission(False, str(e))
            print(f"Submission failed: {str(e)}")
            return False

    def _cleanup(self) -> None:
        """Clean up resources."""
        # Keep browser open briefly to show results
        if self.browser:
            print("\nKeeping browser open for 30 seconds. Press Ctrl+C to close earlier.")
            try:
                import time
                time.sleep(30)
            except KeyboardInterrupt:
                print("\nClosing browser...")

        if self.browser:
            self.browser.close()

        # Clean up session on success
        if self.session:
            session_manager.cleanup_session()


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.agent <job_application_url>")
        print("Example: python -m src.agent 'https://example-ats.com/apply/job-123'")
        sys.exit(1)

    url = sys.argv[1]

    try:
        agent = ApplicationAgent()
        success = agent.run(url)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
