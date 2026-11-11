# Zura123 Dashboard

A small Flask dashboard with a server-side password check, login session, and logout button. The dashboard is intentionally empty so you can add your own content later.

## Important

This repository is currently public. Do not commit passwords, secret keys, API keys, or private data. The password is read from an environment variable and is not stored in this repository. For a real public deployment, use a strong unique password and HTTPS. Do not use the temporary demo password on an internet-facing site.

GitHub Pages cannot run this Flask backend. Deploy this app to a Python hosting service that supports Flask.

## Run locally on Windows

Open PowerShell in the project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DASHBOARD_PASSWORD = "sudo123"
$env:FLASK_SECRET_KEY = py -c "import secrets; print(secrets.token_hex(32))"
py app.py
```

Then open http://127.0.0.1:5000 in your browser.

The value `sudo123` is only a temporary local demo password. Change it to a long, unique password before deploying publicly. Keep `FLASK_SECRET_KEY` private and set both environment variables in your hosting provider's secret/environment settings.

## Routes

- `/` — login page
- `/dashboard` — protected empty dashboard
- `/logout` — end the login session
