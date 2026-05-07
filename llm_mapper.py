"""
LLM-based field mapping: Send form schema and profile to LLM for intelligent mapping.
"""

import json
from typing import Any, Dict, List, Optional
import requests
from config import LLM_API_KEY, LLM_MODEL, LLM_API_BASE, LLM_TEMPERATURE, LLM_TIMEOUT
from logger import logger


class LLMMapper:
    """Map applicant profile to form fields using an LLM."""

    def __init__(self, api_key: str = LLM_API_KEY, model: str = LLM_MODEL, api_base: str = LLM_API_BASE):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base

    def map_profile_to_form(
        self, profile: Dict[str, Any], form_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to map profile data to form fields.

        Args:
            profile: User's applicant profile
            form_schema: Extracted form schema from form_extractor

        Returns:
            Dict with structure:
            {
                "mappings": [
                    {
                        "fieldId": "str",
                        "fieldLabel": "str",
                        "mappedValue": "str|int|bool|null",
                        "confidence": 0.0-1.0,
                        "reason": "str",
                        "requiresManualReview": bool
                    }
                ],
                "unmappedFields": ["fieldId"],
                "notes": "str"
            }
        """
        try:
            # Construct the prompt
            prompt = self._build_prompt(profile, form_schema)

            # Call LLM API
            response_text = self._call_llm(prompt)

            # Parse response
            mapping_result = self._parse_llm_response(response_text)

            return mapping_result

        except Exception as e:
            logger.error("FIELD_MAPPING", f"LLM mapping failed: {str(e)}")
            raise

    def _build_prompt(self, profile: Dict[str, Any], form_schema: Dict[str, Any]) -> str:
        """Build the prompt for the LLM."""
        prompt = f"""You are an expert at mapping job application profile data to web form fields.

Given a user's profile and a job application form, intelligently map each field to the corresponding profile data.

INSTRUCTIONS:
1. For each field in the form, decide:
   - Should this field be auto-filled? (confidence >= 0.8)
   - Should it be flagged for manual review? (confidence 0.5-0.79)
   - Should it be skipped? (confidence < 0.5 or unmappable)

2. For boolean/enum fields (like "Do you have work experience?"), infer from profile data:
   - "Do you have work experience?" -> true if workHistory is not empty
   - "Are you authorized to work?" -> based on visaStatus
   - "Can you start immediately?" -> based on availability.startDate

3. For dropdown options, extract visible options and match to profile:
   - If options are years: match to professional.yearsExperience or count from workHistory
   - If options are job titles: match to professional.title or workHistory titles
   - If options are locations: match to personal.location

4. Return NULL for unmappable fields and explain why.

5. Format your response as valid JSON (no markdown, no code blocks).

USER PROFILE:
{json.dumps(profile, indent=2)}

FORM SCHEMA:
{json.dumps(form_schema, indent=2)}

RESPONSE FORMAT (valid JSON only):
{{
  "mappings": [
    {{
      "fieldId": "field_name",
      "fieldLabel": "Label shown to user",
      "mappedValue": "value to fill",
      "confidence": 0.95,
      "reason": "Why this mapping was chosen",
      "requiresManualReview": false
    }}
  ],
  "unmappedFields": ["fieldId1", "fieldId2"],
  "notes": "Any important notes about the mappings"
}}

Start with the JSON response:"""
        return prompt

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM API and return the response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": LLM_TEMPERATURE,
            "max_tokens": 4000,
        }

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=LLM_TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            logger.error("LLM_API_CALL", f"Failed to call LLM API: {str(e)}")
            raise

    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response JSON."""
        try:
            # Try to extract JSON from response (in case there's surrounding text)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
            else:
                json_str = response_text

            result = json.loads(json_str)

            # Validate structure
            if "mappings" not in result:
                result["mappings"] = []
            if "unmappedFields" not in result:
                result["unmappedFields"] = []
            if "notes" not in result:
                result["notes"] = ""

            return result

        except json.JSONDecodeError as e:
            logger.error("LLM_RESPONSE_PARSE", f"Failed to parse LLM response: {str(e)}")
            raise


# Create a singleton instance
llm_mapper = LLMMapper()
