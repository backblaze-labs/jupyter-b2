# jupyter-b2

[![PyPI](https://img.shields.io/pypi/v/jupyter-b2.svg)](https://pypi.org/project/jupyter-b2/)
[![Python](https://img.shields.io/pypi/pyversions/jupyter-b2.svg)](https://pypi.org/project/jupyter-b2/)
[![License](https://img.shields.io/pypi/l/jupyter-b2.svg)](https://github.com/goanpeca/jupyter-b2/blob/main/LICENSE.txt)
[![CI](https://img.shields.io/github/actions/workflow/status/goanpeca/jupyter-b2/ci.yml?branch=main&label=CI)](https://github.com/goanpeca/jupyter-b2/actions/workflows/ci.yml)
[![codecov](https://img.shields.io/codecov/c/github/goanpeca/jupyter-b2)](https://codecov.io/gh/goanpeca/jupyter-b2)
[![Downloads](https://img.shields.io/pypi/dm/jupyter-b2.svg)](https://pypi.org/project/jupyter-b2/)

**Jupyter/IPython magic commands and fsspec backend for Backblaze B2 Cloud Storage.**

Load datasets, save models, and manage cloud storage — all from your notebook with simple `%b2` commands. No boilerplate, no SDK ceremony.

## Quick Start

```bash
pip install 'jupyter-b2[all]'
```

### One-Time Setup (Recommended)

Authenticate once with the B2 CLI and never think about credentials again:

```bash
pip install b2
b2 account authorize <your-key-id> <your-application-key>
```

### Use in a Notebook

```python
# Auto-authenticates from B2 CLI credentials!
%load_ext jupyter_b2

# Load data straight into a DataFrame
df = %b2_load my-bucket/data/train.csv

# Save results back
%%b2_save my-bucket/results/output.parquet
df
```

## Features

### Magic Commands

| Command | Description |
|---------|-------------|
| `%b2 auth` | Authenticate (interactive, env vars, or B2 CLI credentials) |
| `%b2 status` | Show current authentication status |
| `%b2 buckets` | List all buckets |
| `%b2 ls bucket/prefix/` | List files (with `--recursive`) |
| `%b2 info bucket/file.csv` | File metadata (size, date, SHA1, ID) |
| `%b2 upload local.csv bucket/remote.csv` | Upload file |
| `%b2 download bucket/file.csv ./local.csv` | Download file |
| `%b2 cp bucket/src bucket/dst` | Copy within B2 |
| `%b2 rm bucket/file.csv` | Delete file |
| `%b2 presign bucket/file --expires 3600` | Generate pre-signed URL |
| `df = %b2_load bucket/data.csv` | Load into pandas DataFrame |
| `df = %b2_load bucket/data.parquet --as polars` | Load into Polars DataFrame |
| `text = %b2_load bucket/readme.md --as text` | Load as string |
| `data = %b2_load bucket/model.bin --as bytes` | Load as bytes |
| `obj = %b2_load bucket/config.json --as json` | Load as Python dict |
| `%%b2_save bucket/output.parquet` | Save variable to B2 |

### Smart Format Detection

`%b2_load` auto-detects format from file extension:

| Extension | pandas | polars |
|-----------|--------|--------|
| `.csv` | `read_csv` | `read_csv` |
| `.tsv` | `read_csv(sep='\t')` | `read_csv(separator='\t')` |
| `.parquet` | `read_parquet` | `read_parquet` |
| `.json` | `read_json` | `read_json` |
| `.jsonl` | `read_json(lines=True)` | `read_ndjson` |
| `.feather` | `read_feather` | `read_ipc` |
| `.orc` | `read_orc` | — |
| `.xlsx` | `read_excel` | — |

### fsspec Integration (`b2://` protocol)

With `jupyter-b2[fsspec]`, use B2 paths directly in pandas, polars, dask, and more:

```python
import pandas as pd

# Read directly from B2
df = pd.read_csv("b2://my-bucket/data.csv",
    storage_options={"key_id": "...", "app_key": "..."})

# Write directly to B2
df.to_parquet("b2://my-bucket/output.parquet",
    storage_options={"key_id": "...", "app_key": "..."})
```

### Rich Output

All commands render as beautiful HTML tables in Jupyter — file listings, bucket info, upload confirmations, and metadata cards.

## Authentication

Four methods, tried automatically in this order:

1. **B2 CLI stored credentials** (recommended — zero config after setup):
   ```bash
   pip install b2
   b2 account authorize <key-id> <app-key>
   ```
   After this, `%load_ext jupyter_b2` auto-authenticates every time.

2. **Environment variables** (good for CI/Docker):
   ```bash
   export B2_APPLICATION_KEY_ID="your-key-id"
   export B2_APPLICATION_KEY="your-app-key"
   ```

3. **Explicit credentials**:
   ```python
   %b2 auth --key-id your-key-id --key your-app-key
   ```

4. **Interactive** (prompts for input):
   ```python
   %b2 auth
   ```

## Installation

```bash
# Core magic commands only (Python/IPython)
pip install jupyter-b2

# With fsspec b2:// protocol support
pip install 'jupyter-b2[fsspec]'

# With pandas/pyarrow for DataFrame operations
pip install 'jupyter-b2[pandas]'

# Everything
pip install 'jupyter-b2[all]'

# Development
pip install -e '.[dev]'
```

## Testing Locally

```bash
cd /path/to/jupyter-b2
pip install -e '.[dev]'

# Run unit tests (no B2 credentials needed)
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=jupyter_b2 --cov-report=term-missing

# Linting
ruff check src/ tests/
ruff format --check src/ tests/

# Launch JupyterLab to test interactively
jupyter lab
# Open examples/quickstart.ipynb and run all cells
```

## Examples

See the `examples/` directory:

- **[quickstart.ipynb](examples/quickstart.ipynb)** — All magic commands demonstrated
- **[ml_workflow.ipynb](examples/ml_workflow.ipynb)** — End-to-end ML pipeline with B2

## Looking for a JupyterLab file browser?

Check out [jupyterlab-b2](https://github.com/goanpeca/jupyterlab-b2) — a companion JupyterLab extension that adds a native B2 Cloud Storage file browser to the sidebar, with drag-and-drop upload, file preview, bucket management, and more.

## Requirements

- Python 3.10+
- IPython 7.0+
- b2sdk 2.0+

## License

MIT License. See [LICENSE.txt](LICENSE.txt) for details.
