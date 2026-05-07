"""
Form extraction: Parse DOM and extract form field metadata.
"""

from typing import Any, Dict, List, Optional
from playwright.sync_api import Page


class FormExtractor:
    """Extract form schema and field metadata from a Playwright page."""

    def extract_form_schema(self, page: Page) -> Dict[str, Any]:
        """
        Extract all form fields and their metadata from the page.

        Args:
            page: Playwright page object

        Returns:
            Dict with structure:
            {
                "fields": [
                    {
                        "fieldId": "str",
                        "fieldType": "str",
                        "fieldLabel": "str",
                        "required": bool,
                        "placeholder": "str",
                        "options": [{"value": "str", "label": "str"}, ...],
                        "visible": bool,
                        "validation": {"pattern": "str", "min": int, "max": int}
                    },
                    ...
                ],
                "formId": "str",
                "formAction": "str",
                "formMethod": "str"
            }
        """
        # Extract form metadata and fields using JavaScript
        form_data = page.evaluate(self._extraction_script())

        return form_data

    @staticmethod
    def _extraction_script() -> str:
        """
        JavaScript function to extract form schema.
        This is injected into the page and executed.
        """
        return """
        () => {
            // Helper function to get visible label for a field
            function getFieldLabel(element) {
                // Try associated label
                if (element.id) {
                    const label = document.querySelector(`label[for="${element.id}"]`);
                    if (label) return label.textContent.trim();
                }

                // Try aria-label
                if (element.getAttribute('aria-label')) {
                    return element.getAttribute('aria-label').trim();
                }

                // Try placeholder
                if (element.placeholder) {
                    return element.placeholder.trim();
                }

                // Try closest label (parent)
                const closestLabel = element.closest('label');
                if (closestLabel) {
                    return closestLabel.textContent.trim();
                }

                // Try aria-labelledby
                if (element.getAttribute('aria-labelledby')) {
                    const labelId = element.getAttribute('aria-labelledby');
                    const labelEl = document.getElementById(labelId);
                    if (labelEl) return labelEl.textContent.trim();
                }

                return element.name || element.id || '';
            }

            // Helper function to get field id
            function getFieldId(element) {
                return element.id || element.name || `field_${Math.random().toString(36).substr(2, 9)}`;
            }

            // Helper function to check if element is visible
            function isElementVisible(element) {
                return element.offsetParent !== null && 
                       element.offsetHeight > 0 && 
                       element.offsetWidth > 0 &&
                       window.getComputedStyle(element).visibility !== 'hidden' &&
                       window.getComputedStyle(element).display !== 'none';
            }

            // Helper function to get field type
            function getFieldType(element) {
                const tagName = element.tagName.toLowerCase();
                
                if (tagName === 'input') {
                    return element.type || 'text';
                } else if (tagName === 'select') {
                    return 'select';
                } else if (tagName === 'textarea') {
                    return 'textarea';
                } else if (tagName === 'button') {
                    return 'button';
                } else if (element.getAttribute('contenteditable')) {
                    return 'rich-text';
                }
                return 'unknown';
            }

            // Helper function to extract options for select/radio/checkbox
            function getOptions(element) {
                const options = [];
                const fieldType = getFieldType(element);

                if (fieldType === 'select') {
                    const selectOptions = element.querySelectorAll('option');
                    selectOptions.forEach(opt => {
                        if (opt.value || opt.textContent.trim()) {
                            options.push({
                                value: opt.value || opt.textContent.trim(),
                                label: opt.textContent.trim(),
                                selected: opt.selected
                            });
                        }
                    });
                } else if (fieldType === 'radio' || fieldType === 'checkbox') {
                    // Find all radio/checkbox with same name
                    const groupName = element.name;
                    const sameGroup = document.querySelectorAll(`input[name="${groupName}"]`);
                    sameGroup.forEach(radio => {
                        options.push({
                            value: radio.value,
                            label: getFieldLabel(radio) || radio.value,
                            checked: radio.checked
                        });
                    });
                }

                return options;
            }

            // Main extraction logic
            const form = document.querySelector('form');
            const fields = [];

            if (form) {
                // Find all form inputs
                const allElements = form.querySelectorAll(
                    'input, select, textarea, button, [contenteditable="true"]'
                );

                allElements.forEach(element => {
                    const fieldType = getFieldType(element);
                    
                    // Skip submit/button unless it's the main submit button
                    if (fieldType === 'button' && element.type !== 'submit') {
                        return;
                    }

                    const fieldId = getFieldId(element);
                    const fieldLabel = getFieldLabel(element);
                    const visible = isElementVisible(element);
                    const options = getOptions(element);

                    // Build validation object
                    const validation = {};
                    if (element.pattern) validation.pattern = element.pattern;
                    if (element.min) validation.min = element.min;
                    if (element.max) validation.max = element.max;
                    if (element.maxLength) validation.maxLength = element.maxLength;

                    fields.push({
                        fieldId: fieldId,
                        fieldType: fieldType,
                        fieldLabel: fieldLabel,
                        fieldName: element.name || '',
                        required: element.hasAttribute('required') || element.getAttribute('aria-required') === 'true',
                        placeholder: element.placeholder || '',
                        options: options,
                        visible: visible,
                        disabled: element.disabled,
                        readonly: element.readOnly,
                        validation: Object.keys(validation).length > 0 ? validation : null
                    });
                });
            }

            return {
                fields: fields,
                formId: form ? (form.id || 'form_' + Math.random().toString(36).substr(2, 9)) : '',
                formAction: form ? form.action : '',
                formMethod: form ? (form.method || 'POST') : '',
                fieldCount: fields.length
            };
        }
        """


# Create a singleton instance
form_extractor = FormExtractor()
