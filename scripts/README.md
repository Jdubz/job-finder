# Utility Scripts

Development and debugging scripts for Job Finder.

## Debug Scripts

### debug_firestore.py
Inspects Firestore data structure and displays sample experience entries and blurbs.

```bash
python scripts/debug_firestore.py
```

**Purpose:**
- Verify Firestore connection
- Inspect profile data structure
- Debug profile loading issues

### debug_firestore_raw.py
Displays raw Firestore document data without parsing.

```bash
python scripts/debug_firestore_raw.py
```

**Purpose:**
- View raw Firestore documents
- Debug data format issues
- Inspect field names and types

## Test Scripts

### test_models.py
Tests which Claude AI models are available with your API key.

```bash
python scripts/test_models.py
```

**Purpose:**
- Verify API key works
- Check model availability
- Test AI provider connection

### test_pipeline.py
Tests the complete job search pipeline end-to-end.

```bash
python scripts/test_pipeline.py
```

**Purpose:**
- Full integration test
- Verify all components work together
- Debug pipeline issues

## Usage

All scripts require:
- Environment variables set (`.env` file loaded)
- Virtual environment activated
- Dependencies installed

```bash
# Activate virtual environment
source venv/bin/activate

# Load environment variables
source .env

# Run any script
python scripts/<script-name>.py
```

## Adding New Scripts

Place utility scripts here to keep the project root clean. Scripts should be:
- Self-contained
- Well-documented
- Include error handling
- Load environment variables with `dotenv`
