# Service Specification: Job Application Automator

## 1. System Overview
**Objective:** Automate the parsing and population of web-based Applicant Tracking System (ATS) forms using headless browser automation and an LLM for intelligent data mapping. The system extracts form requirements, intelligently maps user profile data to fields using an LLM, validates mappings with confidence scoring, and populates the DOM. It pauses for manual review before submission to allow verification.

**Primary Domain:** Web Automation / Browser Orchestration + AI-driven data mapping.

**Key Features:**
- Generic form handler (works with any ATS platform)
- Support for complex field types (dropdowns, file uploads, date pickers, dynamic conditional fields, rich text)
- Confidence-based flagging (auto-fill high-confidence fields, flag uncertain ones for review)
- Session persistence and resume capability
- Comprehensive error recovery and validation feedback loop
- Structured logging and audit trail

## 2. Infrastructure Configuration
- **Project Name:** auto-apply-agent
- **Language Stack:** Python 3.11+
- **Browser Automation:** Playwright (sync mode)
- **AI Integration:** LLM API (OpenAI GPT, Claude, etc.) for form field mapping
- **State Management:** Local JSON storage (profile.json, .session.json, .checkpoint.json, application.log)
- **Entry Point:** `agent.py <job_application_url>`

## 3. Data Model: ApplicantProfile

User profile is stored in `profile.json` with the following schema:

```json
{
  "personal": {
    "firstName": "string",
    "lastName": "string",
    "email": "string",
    "phone": "string",
    "location": {
      "city": "string",
      "country": "string"
    }
  },
  "professional": {
    "title": "string",
    "summary": "string (2-3 sentences)",
    "yearsExperience": "number"
  },
  "workHistory": [
    {
      "company": "string",
      "title": "string",
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD or 'Present'",
      "description": "string"
    }
  ],
  "education": [
    {
      "school": "string",
      "degree": "string (e.g., 'Bachelor of Science')",
      "field": "string (e.g., 'Computer Science')",
      "graduationDate": "YYYY-MM-DD"
    }
  ],
  "skills": ["string"],
  "availability": {
    "startDate": "YYYY-MM-DD",
    "noticePeriod": "number (days)"
  },
  "compensation": {
    "currency": "string (e.g., 'USD')",
    "salaryMin": "number",
    "salaryMax": "number"
  },
  "visaStatus": "string (e.g., 'Citizen', 'Green Card', 'H1B sponsorship needed')",
  "files": {
    "resume": "/path/to/resume.pdf",
    "coverLetter": "/path/to/cover_letter.docx (optional)"
  },
  "preferences": {
    "remotePreference": "string (e.g., 'Remote', 'Hybrid', 'On-site', 'No preference')",
    "workplaceType": ["string"] (e.g., ["startup", "enterprise"])
  }
}
```

## 4. System Architecture

### 4.1 Core Components

#### 4.1.1 Form Extractor (`form_extractor.py`)
**Responsibility:** Parse DOM and extract form field metadata.

**Function:** `extract_form_schema(page: Page) -> dict`
- Navigate Playwright page and extract all form elements (input, select, textarea, file input, checkbox, radio, button)
- For each field, capture:
  - `fieldId`: id, name, or data-qa attribute
  - `fieldType`: 'text', 'email', 'number', 'select', 'checkbox', 'radio', 'file', 'textarea', 'date', etc.
  - `fieldLabel`: associated label text or aria-label
  - `required`: boolean (check HTML required attribute)
  - `placeholder`: if present
  - `options`: for select/radio/checkbox (list of {value, label})
  - `visible`: boolean (check if element is in viewport and not hidden)
  - `validation`: pattern, min, max if present
- Return: `{"fields": [...], "formId": "...", "formAction": "...", "method": "..."}`

#### 4.1.2 LLM Mapper (`llm_mapper.py`)
**Responsibility:** Use LLM to intelligently map profile data to form fields.

**Function:** `map_profile_to_form(profile: dict, form_schema: dict, llm_client) -> dict`
- Construct a detailed prompt including:
  - Form schema (field metadata)
  - Applicant profile (all data)
  - Task instructions: "Map profile data to form fields. For each field, decide whether to auto-fill or flag for manual review."
  - Special instructions for:
    - Boolean/enum fields (e.g., "Do you have work experience?" → True/False based on profile.workHistory)
    - Dropdown options (extract visible values, match to profile, return matching value)
    - Multiple possible mappings (prioritize by confidence and specificity)
    - Unmappable fields (return null and reason)
- Send prompt to LLM API with structured output format (JSON)
- Parse LLM response into structured mappings

**LLM Response Format (JSON):**
```json
{
  "mappings": [
    {
      "fieldId": "string",
      "fieldLabel": "string",
      "mappedValue": "string|number|boolean|null",
      "confidence": 0.0,
      "reason": "string",
      "requiresManualReview": false
    }
  ],
  "unmappedFields": ["fieldId"],
  "notes": "string"
}
```

**Confidence Tiers:**
- 0.9-1.0: Auto-fill (high confidence, direct match)
- 0.7-0.89: Auto-fill but flag in review (good match, minor uncertainty)
- 0.5-0.69: Flag for manual review (possible match, ambiguous)
- <0.5: Skip and flag as unfilled (low confidence, skip entirely)

#### 4.1.3 Field Filler (`field_filler.py`)
**Responsibility:** Execute DOM mutations to populate form fields.

**Functions:**
- `fill_text_field(page, fieldId, value)` → Fill input/textarea
- `select_dropdown_option(page, fieldId, value)` → Select from dropdown by value or text
- `check_checkbox(page, fieldId, checked: bool)` → Check/uncheck checkbox
- `select_radio_option(page, fieldId, value)` → Select radio button
- `upload_file(page, fieldId, filePath)` → Upload file to file input
- `fill_date_field(page, fieldId, value, format)` → Fill date picker (detect format from placeholder/aria-label)
- `fill_rich_text_editor(page, fieldId, value)` → Fill contenteditable div or rich text editor

**Error Handling:**
- Catch Playwright errors (element not found, timeout, disabled field)
- Log error with field context
- Return `{success: bool, error: str, fieldId: str}`

#### 4.1.4 Validation Handler (`validation_handler.py`)
**Responsibility:** Detect and handle form validation errors.

**Functions:**
- `trigger_validation(page)` → Trigger form validation (blur all fields)
- `extract_validation_errors(page) -> list` → Capture validation error messages
- `handle_validation_failure(page, fieldId, form_schema, profile, llm_client)` → Ask LLM to re-map field given validation error

#### 4.1.5 Session Manager (`session_manager.py`)
**Responsibility:** Persist and restore application state.

**Data Structures:**
- `.session.json`: `{url, startTime, lastUpdated, filledFields: {fieldId: value, ...}, failedFields: [...], flags: [...], checkpointCount: int}`
- `.checkpoint.json`: `{timestamp, url, filledFieldsCount, failedFieldsCount, state}`

**Functions:**
- `load_session() -> dict` → Load `.session.json` if exists and not expired (>24h)
- `save_session(state)` → Write `.session.json`
- `save_checkpoint(state)` → Write `.checkpoint.json` every 3 fields
- `cleanup_old_sessions()` → Remove sessions older than 24 hours

#### 4.1.6 Logger (`logger.py`)
**Responsibility:** Structured logging for debugging and audit trail.

**Log Format (JSON lines):**
```json
{"timestamp": "2026-05-07T10:30:00Z", "action": "FORM_EXTRACTED", "url": "...", "fieldCount": 12, "status": "SUCCESS"}
{"timestamp": "2026-05-07T10:30:05Z", "action": "FIELD_MAPPED", "fieldId": "email", "mappedValue": "user@example.com", "confidence": 0.95, "status": "SUCCESS"}
{"timestamp": "2026-05-07T10:30:10Z", "action": "FIELD_FILLED", "fieldId": "email", "status": "SUCCESS"}
{"timestamp": "2026-05-07T10:30:15Z", "action": "VALIDATION_ERROR", "fieldId": "phone", "errorMessage": "Invalid phone format", "status": "FAILURE"}
{"timestamp": "2026-05-07T10:30:20Z", "action": "MANUAL_REVIEW_START", "flaggedFields": 3, "status": "SUCCESS"}
{"timestamp": "2026-05-07T10:30:45Z", "action": "SUBMISSION", "approved": true, "status": "SUCCESS"}
```

**Logging Levels:** INFO (action), WARN (flagged field, validation error), ERROR (field fill failure, LLM error)

### 4.2 Orchestration Flow (`agent.py`)

**Main Execution:**
```
1. Load profile from profile.json (fail if not found)
2. Parse command-line argument: job_application_url
3. Check for existing session (resume if applicable)
4. Initialize Playwright browser in headed or headless mode
5. Navigate to job_application_url
6. Extract form schema using form_extractor.extract_form_schema()
7. Call llm_mapper.map_profile_to_form(profile, form_schema)
8. Filter mappings by confidence tier:
   - Auto-fill: confidence >= 0.8
   - Flag: 0.5-0.79
   - Skip: < 0.5
9. For each auto-fill mapping:
   a. Call appropriate field_filler function
   b. Check for field-specific validation errors
   c. If validation error, call validation_handler.handle_validation_failure()
   d. Retry up to 2 times
   e. Log outcome
   f. Save checkpoint every 3 fields
10. After all fields filled, display manual review:
    a. Print filled form state (fieldId, value, confidence)
    b. Highlight flagged fields
    c. Highlight failed fields
    d. Ask user: "Review form in browser. Type 'yes' to submit or 'no' to discard"
11. If 'yes': Submit form and log SUBMISSION success
    If 'no': Close browser and log SUBMISSION cancelled
12. Save final session state and cleanup
```

**Error Recovery:**
- If field injection fails, skip and mark for manual review
- If LLM API fails, pause and ask user for manual action
- If browser closes unexpectedly, save state and allow resume
- If validation loop exceeds max retries (2), flag for manual review

### 4.3 Rate Limiting & Detection Mitigation

- **Delays:** Insert random 500-1500ms delay between field injections (simulate human typing)
- **Page Load Wait:** Use `page.waitForLoadState('networkidle')` before form extraction
- **Headless Detection:** Option to run with `headless: false` (default: false for better success rate)
- **User-Agent:** Use Playwright default (can add rotation later if needed)

## 5. Implementation Phases

### Phase 1: Core MVP (Weeks 1-2)
- [ ] Create project structure and environment setup
- [ ] Define and validate ApplicantProfile schema (`profile.json.template`)
- [ ] Implement Playwright session manager (init, nav, page.waitForLoadState)
- [ ] Implement basic form DOM extraction (text fields, select, textarea)
- [ ] Implement LLM mapper (basic prompting for text fields)
- [ ] Implement field filler (text, select, textarea)
- [ ] Implement manual review UI (terminal-based)
- [ ] Implement structured logging

### Phase 2: Enhanced Field Support (Week 3)
- [ ] File upload handling
- [ ] Checkbox and radio button support
- [ ] Date picker detection and formatting
- [ ] Dynamic field reveal (wait & detect conditional logic)
- [ ] Validation error extraction and feedback loop

### Phase 3: Robustness (Week 4)
- [ ] Confidence scoring and flagging logic
- [ ] Session persistence and resume capability
- [ ] Per-field error recovery (retry, skip, flag)
- [ ] Rate limiting and delays
- [ ] Rich text editor detection and handling

### Phase 4: Polish & Extensibility (Week 5+)
- [ ] Platform-specific adapters (LinkedIn, Greenhouse, Workday)
- [ ] Logging dashboard or CLI reporting tool
- [ ] Performance optimization
- [ ] Integration tests

## 6. File Structure

```
applier/
├── agent.py                    # Main orchestration script
├── form_extractor.py           # DOM parsing and field extraction
├── llm_mapper.py               # LLM-based field mapping
├── field_filler.py             # Playwright automation for field population
├── validation_handler.py        # Validation error detection and retry logic
├── session_manager.py           # State persistence
├── logger.py                    # Structured logging
├── config.py                    # Configuration (LLM API key, timeouts, etc.)
├── profile.json.template        # Template for user profile
├── profile.json                 # User's actual profile (not committed)
├── application.log              # Application audit trail (generated)
├── .session.json                # Current session state (generated)
├── .checkpoint.json             # Last checkpoint (generated)
├── requirements.txt             # Python dependencies
├── README.md                    # Usage instructions
└── SPEC.md                      # This file
```

## 7. Dependencies

- `playwright` - Browser automation
- `python-dotenv` - Environment variable loading
- `requests` - HTTP client for LLM API
- `pydantic` - Data validation
- `typing-extensions` - Type hints

## 8. Configuration & Secrets

**Environment Variables:**
- `LLM_API_KEY` - API key for LLM (OpenAI, Anthropic, etc.)
- `LLM_MODEL` - Model name (e.g., 'gpt-3.5-turbo', 'claude-3-haiku')
- `LLM_API_BASE` (optional) - Custom API endpoint
- `BROWSER_HEADLESS` (optional) - 'true' or 'false' (default: false)

## 9. Usage

```bash
# 1. Set up environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Create and populate profile.json
cp profile.json.template profile.json
# Edit profile.json with your data

# 3. Run agent on a job application URL
python agent.py "https://example-ats.com/apply/job-123"

# 4. Review form in browser, type 'yes' to submit or 'no' to cancel
```

## 10. Verification Strategy

1. **Unit Tests:** Test form extraction, LLM parsing, field filling logic
2. **Integration Tests:** End-to-end flow with mock LLM and test HTML form
3. **Manual Testing:** Test with real ATS platforms (LinkedIn, Greenhouse free tier)
4. **Session Recovery:** Start, pause mid-application, restart, verify resume
5. **Error Resilience:** Inject invalid data, verify validation loop and flagging
6. **Performance:** Measure time per application (target: 2-5 min with review)