# BA Sauerteig

```powershell
# venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# install dev/test deps
pip install -r requirements.txt

# run tests
pytest -q
```

- `pyproject.toml` — minimal project metadata and pytest config
- `requirements.txt` — test dependencies (pytest)
- `src/sourdough/` — example package with `bread.py`
- `tests/` — pytest tests for the example