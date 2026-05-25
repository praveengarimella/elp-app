# ELP App — Experiential Learning Program

A web app for publishing industry projects and collecting student group preferences.

---

## Run locally (first time)

```bash
cd elp-app

# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python main.py
```

Open http://localhost:8000 in your browser.

The SQLite database (`elp.db`) is created automatically on first run.

---

## Pages

| URL | Who | What |
|---|---|---|
| `/` | Students | Browse and search all projects |
| `/preferences` | Students | Submit group details + top 10 preferences |
| `/admin` | Admin | Upload projects, export preferences |

---

## Admin access

Go to http://localhost:8000/admin

- **Username:** `admin`
- **Password:** `elpadmin2027`

To change the password, set environment variables before starting:

```bash
export ADMIN_PASSWORD=yournewpassword
export ADMIN_USERNAME=admin
python main.py
```

---

## Excel upload format

The upload file must be `.xlsx` with these column headers (exact names):

| Column | Description |
|---|---|
| `ELP Project ID` | e.g. `ELP27-001` |
| `Industry Sector` | e.g. `Financial Services` |
| `Problem Type` | e.g. `Strategy`, `Operations` |
| `Problem Description` | Up to ~500 words |
| `Expected Outcomes` | Up to ~500 words |

Re-uploading updates existing projects and adds new ones. Nothing is deleted.

---

## Excel export format

Downloading from `/admin` produces `elp_preferences.xlsx` with:

- Group ID
- 5 × student name + roll number
- Preferences 1–10 (ELP Project IDs in ranked order)
- Submission timestamp

---

## Deploy to Railway (free tier)

1. Push this folder to a GitHub repository.
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub.
3. Select your repo.
4. Railway auto-detects Python. Add a **Start Command**:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
5. Set environment variables in Railway dashboard:
   - `ADMIN_PASSWORD` → your chosen password
6. Done — Railway gives you a public URL.

> **Note:** Railway's free tier uses an ephemeral filesystem, meaning `elp.db` resets on redeploy.
> Before going live, add a Railway Postgres or Volume add-on, or export your data before any redeploy.

---

## Project structure

```
elp-app/
├── main.py            # All routes and app logic
├── database.py        # SQLite connection setup
├── models.py          # Database table definitions
├── requirements.txt
├── elp.db             # Created automatically on first run
└── templates/
    ├── base.html
    ├── projects.html      # Browse page (students)
    ├── preferences.html   # Preference form (students)
    ├── submitted.html     # Success confirmation
    └── admin/
        └── dashboard.html # Admin panel
```
