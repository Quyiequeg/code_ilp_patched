# BA Sauerteig

Minimal Python scaffold added so you can build and run a quick test.

Quick commands (PowerShell):

```powershell
# create and activate a venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install dev/test deps
pip install -r requirements.txt

# run tests
pytest -q
```

Files added:
- `pyproject.toml` — minimal project metadata and pytest config
- `requirements.txt` — test dependencies (pytest)
- `src/sourdough/` — example package with `bread.py`
- `tests/` — pytest tests for the example

If you'd like a different layout (e.g., Poetry, setup.cfg, or additional CI), tell me and I can adjust.

