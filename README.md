# Auto-Apply Agent

Automated job application filler using AI-powered form field mapping.

## Overview

The Auto-Apply Agent uses Playwright for browser automation and an LLM (like GPT-3.5 or Claude) to intelligently map your profile data to any ATS (Applicant Tracking System) web form. It fills fields with high confidence automatically and flags uncertain fields for your review before submission.

## Features

- **Intelligent Field Mapping**: Uses LLM to understand form context and map profile data accurately
- **Multi-field Type Support**: Text, email, select dropdowns, checkboxes, file uploads, date pickers, rich text editors
- **Confidence Scoring**: Auto-fills high-confidence matches, flags uncertain ones for review
- **Error Recovery**: Detects validation errors and attempts alternative values
- **Session Persistence**: Resume interrupted applications from checkpoints
- **Manual Review**: Always pauses before final submission for your verification
- **Audit Trail**: Comprehensive logging for debugging and tracking

## Setup

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your LLM API credentials:

```bash
cp .env.example .env
# Edit .env with your LLM API key and model
```

**Required:**
- `LLM_API_KEY`: Your LLM API key (OpenAI, Anthropic, etc.)
- `LLM_MODEL`: Model name (e.g., `gpt-3.5-turbo` or `claude-3-haiku-20240307`)

**Optional:**
- `LLM_API_BASE`: Custom API endpoint (default: `https://api.openai.com/v1`)
- `BROWSER_HEADLESS`: Run browser in headless mode (default: `false`)
- `BROWSER_TIMEOUT`: Browser timeout in ms (default: `30000`)
- `FIELD_FILL_DELAY_MIN`: Min delay between field fills in ms (default: `500`)
- `FIELD_FILL_DELAY_MAX`: Max delay between field fills in ms (default: `1500`)

### 3. Create Your Profile

Copy the template and fill in your information:

```bash
cp profile.json.template profile.json
# Edit profile.json with your actual data
```

**Profile includes:**
- Personal info (name, email, phone, location)
- Professional summary and years of experience
- Work history
- Education
- Skills
- Availability and notice period
- Compensation expectations
- Visa status
- Resume and cover letter file paths
- Work preferences

## Usage

### Run Agent on a Job Application

```bash
python agent.py "https://example-ats.com/apply/job-123"
```

### Workflow

1. **Form Extraction**: Agent navigates to the URL and extracts all form fields
2. **AI Mapping**: LLM analyzes form fields and maps profile data with confidence scores
3. **Auto-Fill**: Fields with high confidence (≥80%) are automatically filled
4. **Review**: Agent pauses for manual review of:
   - Auto-filled fields (verify correct)
   - Flagged fields (manual suggestion of alternative values)
   - Failed fields (manually entered)
5. **Submit**: You approve or cancel before final submission

### Output

After running, you'll see:
- `application.log` - JSON-line audit trail of all actions
- `.session.json` - Current session state (resume capability)
- `.checkpoint.json` - Last checkpoint for recovery

## Architecture

### Core Modules

- **`agent.py`** - Main orchestration and workflow
- **`form_extractor.py`** - DOM parsing to extract field metadata
- **`llm_mapper.py`** - LLM integration for field mapping
- **`field_filler.py`** - Playwright automation to populate fields
- **`validation_handler.py`** - Detect and recover from validation errors
- **`session_manager.py`** - State persistence and resume capability
- **`logger.py`** - Structured logging for audit trail
- **`config.py`** - Configuration and environment setup

### Data Models

**ApplicantProfile** (`profile.json`):
```json
{
  "personal": {...},
  "professional": {...},
  "workHistory": [...],
  "education": [...],
  "skills": [...],
  "availability": {...},
  "compensation": {...},
  "visaStatus": "...",
  "files": {...},
  "preferences": {...}
}
```

## Advanced Usage

### Resume Interrupted Application

If the process is interrupted, you can resume from where it left off:

```bash
python agent.py "https://example-ats.com/apply/job-123"
# Will resume from last session/checkpoint
```

### Adjust LLM Confidence Thresholds

Edit `agent.py` to change:
- Auto-fill threshold: `if confidence >= 0.8:`
- Manual review threshold: `else:` (< 0.8)

### Use Different LLM Model

Update `.env`:
```bash
LLM_MODEL=gpt-4  # or claude-3-sonnet-20240229, etc.
```

### Toggle Headless Mode

Set in `.env`:
```bash
BROWSER_HEADLESS=true  # false for visible browser (default)
```

## Troubleshooting

### Form Not Detected

- Check that the page has loaded fully (wait for network idle)
- Verify form exists with `<form>` tag or form-like structure
- Use `BROWSER_HEADLESS=false` to see what the agent sees

### Fields Not Filling

- Check `application.log` for specific errors
- Verify field selectors (ID or name attributes) are valid
- Try manually entering a value to verify field is not disabled/readonly
- Increase `FIELD_FILL_DELAY_MAX` if form is slow to respond

### LLM Mapping Issues

- Verify LLM API key and model name in `.env`
- Check profile.json has all expected data
- Review LLM response in logs for parsing errors
- Consider using more capable model if mappings are poor

### Session Resume Not Working

- Delete `.session.json` to start fresh
- Verify session URL matches the URL you're applying to
- Session expires after 24 hours (configurable via `SESSION_EXPIRY_HOURS`)

## Limitations

- **Complex forms**: Dynamic multi-step forms may not work as expected
- **CAPTCHA**: The agent pauses for manual review, so you can handle CAPTCHA
- **File uploads**: Requires file paths to exist locally
- **Rich UI frameworks**: Forms built with React/Vue/Angular may need special handling
- **Detection**: Some ATS systems may detect automation; `BROWSER_HEADLESS=false` helps

## Future Enhancements

- [ ] Platform-specific adapters (LinkedIn, Greenhouse, Workday)
- [ ] Cover letter personalization based on job description
- [ ] Multi-application bulk mode
- [ ] Scheduled/recurring applications
- [ ] Analytics dashboard
- [ ] Support for MFA and CAPTCHA solving services

## License

MIT

## Support

For issues or questions:
1. Check `application.log` for error details
2. Review the troubleshooting section above
3. Ensure LLM API credentials are correct
4. Try with `BROWSER_HEADLESS=false` to debug visually

---

**Note**: This tool is intended for legitimate job applications where you own the profile data. Always review before final submission to ensure accuracy.
