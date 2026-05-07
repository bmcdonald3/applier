"""
Structured logging for audit trail and debugging.
"""

import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from config import LOG_FILE


class ApplicationLogger:
    """Structured JSON-line logger for application events."""

    def __init__(self, log_file: str = LOG_FILE):
        self.log_file = log_file

    def _format_log_entry(
        self,
        action: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format a log entry with timestamp and standard fields."""
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "action": action,
            "status": status,
        }
        if details:
            entry.update(details)
        return entry

    def _write_log(self, entry: Dict[str, Any]) -> None:
        """Write log entry to file and optionally to stdout."""
        log_line = json.dumps(entry)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")
        # Also print to stderr for visibility
        print(log_line, file=sys.stderr)

    def form_extracted(self, url: str, field_count: int, **extra):
        """Log form extraction."""
        self._write_log(
            self._format_log_entry(
                "FORM_EXTRACTED",
                "SUCCESS",
                {"url": url, "fieldCount": field_count, **extra},
            )
        )

    def field_mapped(
        self,
        field_id: str,
        field_label: str,
        mapped_value: Any,
        confidence: float,
        requires_review: bool,
        **extra,
    ):
        """Log field mapping."""
        self._write_log(
            self._format_log_entry(
                "FIELD_MAPPED",
                "SUCCESS",
                {
                    "fieldId": field_id,
                    "fieldLabel": field_label,
                    "mappedValue": str(mapped_value)[:100],  # Truncate long values
                    "confidence": confidence,
                    "requiresManualReview": requires_review,
                    **extra,
                },
            )
        )

    def field_filled(self, field_id: str, status: str = "SUCCESS", error: Optional[str] = None, **extra):
        """Log field population."""
        details = {"fieldId": field_id, **extra}
        if error:
            details["error"] = error
        self._write_log(self._format_log_entry("FIELD_FILLED", status, details))

    def validation_error(
        self, field_id: str, error_message: str, attempt: int = 1, **extra
    ):
        """Log validation error."""
        self._write_log(
            self._format_log_entry(
                "VALIDATION_ERROR",
                "FAILURE",
                {
                    "fieldId": field_id,
                    "errorMessage": error_message,
                    "attemptNumber": attempt,
                    **extra,
                },
            )
        )

    def manual_review_start(self, flagged_field_count: int, unfilled_field_count: int, **extra):
        """Log manual review phase."""
        self._write_log(
            self._format_log_entry(
                "MANUAL_REVIEW_START",
                "SUCCESS",
                {
                    "flaggedFieldCount": flagged_field_count,
                    "unfilledFieldCount": unfilled_field_count,
                    **extra,
                },
            )
        )

    def submission(self, approved: bool, error: Optional[str] = None, **extra):
        """Log form submission."""
        status = "SUCCESS" if approved else ("FAILURE" if error else "CANCELLED")
        details = {"approved": approved, **extra}
        if error:
            details["error"] = error
        self._write_log(self._format_log_entry("SUBMISSION", status, details))

    def error(self, action: str, error_message: str, **extra):
        """Log generic error."""
        self._write_log(
            self._format_log_entry(
                action,
                "ERROR",
                {"error": error_message, **extra},
            )
        )

    def info(self, action: str, message: str, **extra):
        """Log informational message."""
        self._write_log(
            self._format_log_entry(
                action,
                "INFO",
                {"message": message, **extra},
            )
        )


# Global logger instance
logger = ApplicationLogger()
