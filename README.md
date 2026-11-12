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

## Download and run on another Windows computer

After this project is published to GitHub, the user can select **Code → Download
ZIP**, extract the folder, and run `scripts\setup_windows.ps1` in PowerShell.
Alternatively, clone it with Git. Setup creates a local Python virtual
environment, installs dependencies, and builds the frontend; it does not
require an installer or administrator access.

Requirements are Git (for cloning), Python 3.10+, and Node.js 20+. To start the
app, run these commands from the extracted project folder in PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_windows.ps1
```

The start script opens the browser and runs the API on
the local computer. Keep the PowerShell window open while using the app;
press Ctrl+C to stop the server. The database is stored under
`%LOCALAPPDATA%\MathTestGenerator`, separate from the downloaded source folder.

For updates, a Git checkout can use `git pull` and rerun
`scripts\setup_windows.ps1`; the local database remains intact. ZIP downloads
must be downloaded and extracted again for updates.

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
