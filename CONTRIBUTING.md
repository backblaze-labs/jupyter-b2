# Contributing to b2-jupyter

Thank you for your interest in contributing to b2-jupyter!

## Development Setup

```bash
# Clone the repo
git clone https://github.com/backblaze-b2-samples/b2-jupyter.git
cd b2-jupyter

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in development mode with all dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=b2_jupyter --cov-report=term-missing

# Run specific test file
pytest tests/test_magics/test_loaders.py -v
```

## Code Style

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check style
ruff check src/ tests/
ruff format --check src/ tests/

# Auto-fix
ruff check --fix src/ tests/
ruff format src/ tests/
```

## Type Checking

```bash
mypy src/b2_jupyter/ --ignore-missing-imports
```

## Project Structure

```
src/b2_jupyter/
  __init__.py                    # Extension entry point (load_ipython_extension)
  magics/
    __init__.py
    b2_magics.py                 # Core magic commands (%b2, %b2_load, %%b2_save)
    auth.py                      # Authentication management
    display.py                   # Rich HTML display formatters
    loaders.py                   # Data loading (pandas, polars, text, bytes, json)
  fsspec_backend/
    __init__.py
    filesystem.py                # fsspec B2FileSystem (b2:// protocol)
  lab_extension/
    __init__.py                  # Planned JupyterLab extension
```

## Adding a New Magic Command

1. Add the handler method to `B2Magics` in `b2_magics.py`
2. Register it in the `dispatch` dict in the `b2` method
3. Add tests in `tests/test_magics/`
4. Update the help text in `_print_help()`
5. Add examples in the quickstart notebook

## Submitting Changes

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes with tests
4. Run the full test suite: `pytest tests/ -v`
5. Run linting: `ruff check src/ tests/`
6. Submit a pull request
