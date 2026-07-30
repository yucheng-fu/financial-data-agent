# Agents.md

## Overview
This markdown file defines the overall project structure and code style used in the project.

### Code repository
When asked to update the code repository structure, only include the folders, do not include individual files. Next to the folder name, give a short summary of its contents.

```text
.
├── data/ - Stored artifacts such as downloaded filings and generated datasets.
└── src/ - Python source code for the application package.
    └── financial_data_agent/ - Main package namespace for financial data agent functionality.
        ├── api/ - API layer and request/response handling.
        └── backend/ - Backend fetchers and data acquisition helpers.
```


### Code style 
Follow the standards defined in the `pyproject.toml` file.
- Avoid writing unnecessary comments inline.
- Avoid defining functions within functions.
- Avoid implementing "fallbacks" unless explicitly prompted.
- Every function should include type hints for inputs and outputs.
- Docstring format: Follow the autoDocstring format.

### Tests
Unit tests are placed in `tests/` and the name convention is to use `test_` prefix.

### Common commands
- Run all tests: `pytest`
- Lint and format (ruff): `ruff check .` and `ruff format .`

### Agent guardrails
- Keep test updates close to behavior changes and use explicit test names describing what is validated.
- Avoid broad refactors unless requested; prioritize minimal, verifiable changes.
