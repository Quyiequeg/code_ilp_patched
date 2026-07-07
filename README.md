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

Beispiel

Angenommen dein Projekt liegt hier:

C:\Users\Max\Bachelorarbeit\code
1. CMD öffnen

Windows

→ Win + R

→ cmd

→ Enter

2. In den Projektordner wechseln
cd C:\Users\Max\Bachelorarbeit\code

Jetzt befindet sich die Konsole in deinem Projekt.

3. Dokumentation erzeugen

Später genügt beispielsweise

sphinx-build -b latex docs docs\_build\latex

Danach

cd docs\_build\latex

und

make.bat

Nun entsteht automatisch

Projektname.pdf