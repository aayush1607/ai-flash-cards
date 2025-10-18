# AI Flash Cards Test Suite

This directory contains all tests and utility scripts for the AI Flash Cards application.

## Directory Structure

```
test/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for API endpoints
├── scripts/        # Utility scripts for testing and development
├── run_tests.py    # Test runner script
└── README.md       # This file
```

## Running Tests

### Run All Tests
```bash
python test/run_tests.py
```

### Run Specific Test Categories
```bash
# Unit tests only
python test/unit/test_config.py
python test/unit/test_db_path.py

# Integration tests only
python test/integration/test_api.py

# Utility scripts
python test/scripts/run_ingestion.py
```

## Test Categories

### Unit Tests (`test/unit/`)
- **test_config.py**: Configuration management tests
- **test_db_path.py**: Database path validation tests
- **test_direct_db.py**: Direct database operation tests

### Integration Tests (`test/integration/`)
- **test_api.py**: API endpoint functionality tests
- **test_api_context.py**: API context and workflow tests

### Utility Scripts (`test/scripts/`)
- **run_ingestion.py**: Data ingestion pipeline script

## Adding New Tests

1. **Unit Tests**: Add to `test/unit/` with prefix `test_`
2. **Integration Tests**: Add to `test/integration/` with prefix `test_`
3. **Utility Scripts**: Add to `test/scripts/` with descriptive names

## Test Naming Convention

- Unit tests: `test_<component>.py`
- Integration tests: `test_<feature>.py`
- Utility scripts: `<action>_<target>.py`

## Dependencies

All tests should be run from the project root directory to ensure proper import paths.
