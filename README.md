# HR Analytics Dashboard (HCM Lite)

A Streamlit HR dashboard with employee, attendance, leave, company-settings, salary, and department-analysis pages.

## Requirements
- Python 3.10 or newer
- Internet connection for installing packages

## Run locally

Open a terminal in this project folder and run:

```bash
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows Command Prompt**
```bat
.venv\Scripts\activate.bat
```

Install dependencies and launch:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL shown in the terminal (usually `http://localhost:8501`).

## First login
The included `data/users.json` is intentionally empty so the app shows **First-Time Company Setup**. Create a new admin account in the app. Passwords are stored as hashes, not plain text.

## Notes
- Do not upload `.venv`, passwords, or real employee data to a public repository.
- The dashboard analytics use the CSV in `data/`.
- JSON files in `data/` store local demo records and can be reset for a clean demo.
