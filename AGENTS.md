# Agents.md

## Overview
This markdown file defines the overall project structure and code style used in the project.

### Code repository
When asked to update the code repository structure, only include the folders, do not include individual files. Next to the folder name, give a short summary of its contents.

```text
```


### Code style 
Follow the standards defined in the `pyproject.toml` file.
- Avoid writing unnecessary comments inline.
- Avoid defining functions within functions.
- Avoid implementing "fallbacks" unless explicitly prompted.
- Docstring format: Follow the autoDocstring format. 

### Tests
Unit tests are placed in `tests/` and the name convention is to use `test_` prefix.

### Common commands
- Run all tests: `pytest`
- Lint and format (ruff): `ruff check .` and `ruff format .`

### Agent guardrails
- Keep test updates close to behavior changes and use explicit test names describing what is validated.
- Avoid broad refactors unless requested; prioritize minimal, verifiable changes.
