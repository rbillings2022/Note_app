# Name: Romario Billings
# Description
## Note tasking app
- A simple app where you can write a note and save/load that text.
## Setup

### Prerequisites
- Python 3.9 or later installed
- pip

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd Note_app
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv noteapp-env
noteapp-env\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv noteapp-env
source noteapp-env/bin/activate
```

You'll know it worked when your terminal prompt shows `(noteapp-env)` at the start of the line.

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Initialize the database
Run this once to create `notebook.db` with the required tables:
```bash
python src/services/schema.py
```

### 5. Run the app
```bash
python src/services/server.py
```

You should see:

Open **http://127.0.0.1:8000** in your browser — it will redirect you to the registration/login page.

### Stopping the server
Press `Ctrl+C` in the terminal.

### Deactivating the virtual environment
```bash
deactivate
```

## Tech Stack Architecture. 
- Frontend: HTML, JS, CSS
- Backend API: python
- Package Tech: unvicorn, fastapi
- Database: sqlite
