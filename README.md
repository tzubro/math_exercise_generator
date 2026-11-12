# Math Test Generator

A local teacher app using React, TypeScript, FastAPI, and SQLite. The exercise
bank supports adding, editing, searching, filtering, attaching images, deleting,
and importing draft questions. Teachers can compose tests and export DOCX files;
PDF export requires LibreOffice.

## Development

1. Install frontend dependencies and build the app:

   ```powershell
   cd frontend
   npm.cmd install
   npm.cmd run build
   ```

2. Install backend dependencies and start FastAPI from the project root:

   ```powershell
   py -m pip install -r backend/requirements.txt
   py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
   ```

3. Open `http://127.0.0.1:8000`. FastAPI serves the built frontend and API
   from the same origin. The Vite development server is available with
   `npm.cmd run dev` in `frontend`; it proxies `/api` to FastAPI on port 8000.

See [docs/API_CONTRACT.md](docs/API_CONTRACT.md) for shared models, API shapes,
and module boundaries. SQLite data is stored under the current user's local
application data directory; set `MATH_TEST_GENERATOR_DATA_DIR` to override it.

## Install on another Windows computer

Download `MathTestGenerator-Setup-<version>-x64.exe` from the repository's
[GitHub Releases](https://github.com/tzubro/math_exercise_generator/releases)
page, run it, and launch the app from the Start menu or
optional desktop shortcut. The installer is per-user and does not require
administrator access, Python, or Node.js. The app opens in the browser and runs
locally on that computer.

The database remains under `%LOCALAPPDATA%\MathTestGenerator` when the app is
updated or uninstalled. To release an update, push a version tag such as
`v0.1.0`; GitHub Actions builds the Windows installer and attaches it to the
corresponding release.

Developers who want to run from source can use the separate
`scripts\setup_windows.ps1` and `scripts\start_windows.ps1` scripts. Those
require Python 3.10+ and Node.js 20+.

Ollama is optional and is not bundled. Local AI import uses the configured
Ollama model; the user must install Ollama and pull that model separately.
PDF export also requires LibreOffice. DOCX export and the other app features
work without either program. Setup downloads Python and JavaScript packages, so
an internet connection is needed during initial setup and updates.

## Backend tests

```powershell
py -m pip install -r backend/requirements-dev.txt
py -m pytest backend/tests -q
```
