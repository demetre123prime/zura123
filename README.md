# Zura Dashboard

A small, password-protected dashboard for keeping a **manual inventory of your own devices** and recording check-ins and notes.

## What it does

- Password-protected login and logout.
- Add and remove device entries manually.
- Record a manual check-in for a device.
- Add notes to the activity feed.
- Store records in SQLite.
- CSRF protection on forms and basic browser security headers.

This project does **not** install agents, monitor devices, collect browser data, read files, capture keystrokes, or collect passwords/tokens. A device is listed only when you add it yourself.

## Run locally on Windows (PowerShell)

Python 3.10+ is recommended.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DASHBOARD_PASSWORD = "choose-a-long-unique-password"
$env:FLASK_SECRET_KEY = (py -c "import secrets; print(secrets.token_hex(32))")
$env:COOKIE_SECURE = "0"
py app.py
```

Open http://127.0.0.1:5000.

## Deploy

This is a Flask application, not a GitHub Pages site. Deploy it to a Python host that supports a persistent disk for SQLite, set these environment variables in the host dashboard, and use HTTPS:

- `DASHBOARD_PASSWORD`: a unique password of at least 12 characters.
- `FLASK_SECRET_KEY`: a random secret of at least 32 characters.
- `COOKIE_SECURE`: leave as `1` when using HTTPS.
- `DATABASE_PATH`: optional path on the host's persistent disk, e.g. `/var/data/dashboard.db`.

The included `render.yaml` is a deployment blueprint. Review the host's current pricing and persistent-disk availability before deploying.

## Security notes

- Never commit real passwords, API keys, or secret keys.
- The repository is public, so keep all secrets in environment variables.
- Use a strong unique dashboard password; do not reuse your GitHub password.
- Back up the SQLite database if you need to preserve your records.
