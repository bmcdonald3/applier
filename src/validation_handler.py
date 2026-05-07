"""
Validation handler: Detect and handle form validation errors.
"""

from typing import Any, Dict, List, Optional
from playwright.sync_api import Page
from .logger import logger


class ValidationHandler:
    """Handle form validation errors and provide feedback."""

    def extract_validation_errors(self, page: Page) -> List[Dict[str, str]]:
        """
        Extract validation error messages from the page.

        Returns:
            List of dicts with fieldId and error message
        """
        # Trigger validation by dispatching blur events on all fields
        self.trigger_validation(page)

        # Extract error messages using JavaScript
        errors = page.evaluate("""
            () => {
                const errors = [];
                
                // Check for error messages near fields
                const errorElements = document.querySelectorAll(
                    '.error, .invalid, [role="alert"], .form-error, .error-message'
                );
                
                errorElements.forEach(el => {
                    // Try to find associated field
                    const parent = el.closest('.form-group, .field-wrapper, .input-group, [data-field]');
                    let fieldId = null;
                    
                    if (parent) {
                        const field = parent.querySelector('input, select, textarea');
                        if (field) {
                            fieldId = field.id || field.name;
                        }
                    }
                    
                    errors.push({
                        fieldId: fieldId || 'unknown',
                        message: el.textContent.trim()
                    });
                });

                // Also check HTML5 validation messages
                const invalidFields = document.querySelectorAll('input:invalid, select:invalid, textarea:invalid');
                invalidFields.forEach(field => {
                    errors.push({
                        fieldId: field.id || field.name,
                        message: field.validationMessage || 'Invalid input'
                    });
                });

                return errors;
            }
        """)

        return errors

    def trigger_validation(self, page: Page) -> None:
        """Trigger form validation by firing blur events."""
        page.evaluate("""
            () => {
                const fields = document.querySelectorAll('input, select, textarea');
                fields.forEach(field => {
                    field.dispatchEvent(new Event('blur', { bubbles: true }));
                    field.dispatchEvent(new Event('change', { bubbles: true }));
                });
            }
        """)

    def handle_validation_failure(
        self,
        page: Page,
        field_id: str,
        field_type: str,
        current_value: Any,
        form_schema: Dict[str, Any],
        profile: Dict[str, Any],
        llm_mapper: "LLMMapper",
        attempt: int = 1,
    ) -> Optional[Any]:
        """
        Handle validation failure by asking LLM for alternative mapping.

        Args:
            page: Playwright page
            field_id: Failed field ID
            field_type: Field type
            current_value: Value that failed validation
            form_schema: Form schema
            profile: User profile
            llm_mapper: LLM mapper instance
            attempt: Current retry attempt

        Returns:
            New value to try, or None if unable to recover
        """
        # Extract validation error
        errors = self.extract_validation_errors(page)
        error_msg = next(
            (e["message"] for e in errors if e["fieldId"] == field_id),
            "Validation failed",
        )

        logger.validation_error(field_id, error_msg, attempt)

        # Find the field in form schema
        field_info = next(
            (f for f in form_schema.get("fields", []) if f["fieldId"] == field_id),
            None,
        )

        if not field_info:
            return None

        # Ask LLM to suggest alternative value
        try:
            alternative_value = self._ask_llm_for_alternative(
                field_id,
                field_type,
                current_value,
                error_msg,
                field_info,
                profile,
                llm_mapper,
            )
            return alternative_value
        except Exception as e:
            logger.error(
                "VALIDATION_RETRY",
                f"Failed to get alternative value from LLM: {str(e)}",
            )
            return None

    @staticmethod
    def _ask_llm_for_alternative(
        field_id: str,
        field_type: str,
        current_value: Any,
        error_msg: str,
        field_info: Dict[str, Any],
        profile: Dict[str, Any],
        llm_mapper: "LLMMapper",
    ) -> Optional[Any]:
        """Ask LLM for an alternative value given a validation error."""
        import json

        prompt = f"""Given a validation error on a form field, suggest an alternative value from the user's profile.

FIELD INFO:
- ID: {field_id}
- Type: {field_type}
- Label: {field_info.get('fieldLabel', '')}
- Options: {json.dumps(field_info.get('options', []))}
- Validation: {json.dumps(field_info.get('validation', {}))}

CURRENT VALUE (failed): {current_value}
VALIDATION ERROR: {error_msg}

USER PROFILE:
{json.dumps(profile, indent=2)}

Suggest a single alternative value that might pass validation. 
Return ONLY the value (no quotes, no explanation):"""

        response = llm_mapper._call_llm(prompt)
        return response.strip()


# Create a singleton instance
validation_handler = ValidationHandler()
