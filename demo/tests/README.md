# UNTP Schema and Context Validation Tests

This directory contains tests for validating UNTP credentials against their JSON schemas and JSON-LD contexts.

## Files

- `test_pydantic_schemas.py` - Tests Pydantic models against UNTP schemas
- `test_context_validation.py` - Tests that credentials use terms defined in JSON-LD contexts
- `TEST_RESULTS.md` - Documentation of test results and findings

## Running Tests

### 1. Test Pydantic Models (JSON Schema)

Tests that our Pydantic models generate valid JSON according to UNTP schemas:

```bash
cd demo
uv run python tests/test_pydantic_schemas.py
```

### 2. Test JSON-LD Context Validation

Validates that credentials only use terms defined in their JSON-LD contexts:

```bash
cd demo
uv run python tests/test_context_validation.py
```

### 3. Validate Individual Credentials

You can validate individual credentials from the explorer:

```bash
# 1. Run the demo
cd demo
uv run python demo_script.py http://localhost:8000

# 2. Visit http://localhost:8000/explorer/credentials

# 3. Click on a credential and copy the "Full JSON"

# 4. Validate it using Python:
python3 << 'EOF'
import asyncio
from tests.test_context_validation import validate_credential_json

credential_json = '''
{
  "@context": [...],
  "type": ["VerifiableCredential", "DigitalConformityCredential"],
  ...
}
'''

asyncio.run(validate_credential_json(credential_json))
EOF
```

## What Gets Validated

### JSON Schema Validation
- Structure and data types
- Required fields
- Enum values
- Nested object schemas

### JSON-LD Context Validation
- All property names exist in the context
- Context URLs match credential types
- Terms from W3C Credentials context
- UNTP-specific terms

### Expected Context URLs

- **DCC**: `https://test.uncefact.org/vocabulary/untp/dcc/0.6.0/`
- **DIA**: `https://test.uncefact.org/vocabulary/untp/dia/0.6.0/`
- **DPP**: `https://test.uncefact.org/vocabulary/untp/dpp/0.6.0/`

## Common Issues

### "Undefined terms in context"
This means you're using properties that aren't defined in the UNTP JSON-LD context. Check:
- The property name spelling
- Whether it's a custom extension
- If it should be in a nested object

### "Schema validation failed"
This means the credential structure doesn't match the JSON schema. Check:
- Required fields are present
- Data types match (string, number, boolean, array, object)
- Enum values are correct
- Object nesting matches the schema
