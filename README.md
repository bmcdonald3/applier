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

## Quick Start

### 1. Setup (One Command)

```bash
bash setup.sh
```

Or manually:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
# Copy environment template
cp config/.env.example .env

# Copy profile template
cp config/profile.json.template profile.json

# Edit both files with your information
nano .env
nano profile.json
```

### 3. Run

```bash
python agent.py "https://example-ats.com/apply/job-123"
```

## Configuration

### Environment Variables (`.env`)

**Required:**
- `LLM_API_KEY` - Your LLM API key (OpenAI, Anthropic, etc.)
- `LLM_MODEL` - Model name (e.g., `gpt-3.5-turbo`, `claude-3-haiku-20240307`)

**Optional:**
- `LLM_API_BASE` - Custom API endpoint (default: `https://api.openai.com/v1`)
- `BROWSER_HEADLESS` - Run browser in headless mode (default: `false`)
- `BROWSER_TIMEOUT` - Browser timeout in ms (default: `30000`)
- `FIELD_FILL_DELAY_MIN` - Min delay between field fills (default: `500`)
- `FIELD_FILL_DELAY_MAX` - Max delay between field fills (default: `1500`)

See `config/.env.example` for all options.

### Applicant Profile (`profile.json`)

Edit your profile with:
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

See `config/profile.json.template` for the full structure.

## Project Structure

```
applier/
├── src/                         # Source code
│   ├── __init__.py
│   ├── agent.py                # Main orchestration
│   ├── config.py               # Configuration
│   ├── form_extractor.py       # Form parsing
│   ├── llm_mapper.py           # LLM integration
│   ├── field_filler.py         # Field population
│   ├── validation_handler.py   # Error recovery
│   ├── session_manager.py      # State persistence
│   └── logger.py               # Structured logging
├── tests/                       # Test suite
├── config/                      # Configuration templates
│   ├── .env.example
│   └── profile.json.template
├── agent.py                    # Entry point
├── setup.sh                    # Setup script
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── SPEC.md                     # Technical specification
└── .gitignore                  # Git ignore rules
```

## Usage

### Basic Usage

```bash
python agent.py "https://example-ats.com/apply/job-123"
```

### Workflow

1. **Form Extraction**: Agent navigates to the URL and extracts all form fields
2. **AI Mapping**: LLM analyzes form fields and maps profile data with confidence scores
3. **Auto-Fill**: Fields with high confidence (≥80%) are automatically filled
4. **Review**: Agent pauses for manual review of:
   - Auto-filled fields (verify correct)
   - Flagged fields (low confidence suggestions)
   - Failed fields (manually entered)
5. **Submit**: You approve or cancel before final submission

### Output Files

After running, you'll see:
- `application.log` - JSON-line audit trail of all actions
- `.session.json` - Current session state (for resume capability)
- `.checkpoint.json` - Last checkpoint (for recovery)

### Resume Interrupted Application

If the process is interrupted, you can resume from where it left off:

```bash
python agent.py "https://example-ats.com/apply/job-123"
# Will resume from last session/checkpoint if available
```

## Advanced Configuration

### Use Different LLM Model

Edit `.env`:
```bash
LLM_MODEL=gpt-4  # or claude-3-sonnet, etc.
```

### Toggle Headless Mode

For debugging, run with visible browser:
```bash
BROWSER_HEADLESS=false python agent.py "https://..."
```

### Adjust Confidence Thresholds

Edit `src/agent.py`:
```python
if confidence >= 0.8:  # Auto-fill threshold
    # Auto-fill
else:
    # Flag for manual review
```

## Troubleshooting

### Setup Issues

- Ensure you're running Python 3.7+
- If `bash setup.sh` fails, run commands manually
- On Windows, use `python` instead of `python3`

### Form Not Detected

- Verify form has loaded fully (wait for network idle)
- Ensure form exists with `<form>` tag or form-like structure
- Use `BROWSER_HEADLESS=false` in `.env` to see what the agent sees
- Check browser console for JavaScript errors

### Fields Not Filling

- Check `application.log` for specific errors
- Verify field selectors (ID or name attributes) are valid
- Try manually entering a value to verify field is not disabled
- Increase `FIELD_FILL_DELAY_MAX` if form is slow

### LLM Mapping Issues

- Verify LLM API key and model in `.env` are correct
- Check profile.json has complete data
- Review `application.log` for LLM response errors
- Try with a more capable model if mappings are poor

### Session Resume Not Working

- Delete `.session.json` to start fresh
- Verify session URL matches the URL you're applying to
- Sessions expire after 24 hours (configurable via `SESSION_EXPIRY_HOURS`)

## Security & Privacy

- Profile data is stored locally as JSON (not encrypted)
- LLM API calls transmit only form schema and profile data
- No data is stored on external servers
- Session files are temporary and local
- Sensitive files (.env, profile.json) are in `.gitignore`

## License

MIT

---

**Note**: This tool is intended for legitimate job applications. Always review before final submission to ensure accuracy and compliance with each job board's terms of service.
