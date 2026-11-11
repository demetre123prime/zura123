import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "dashboard.db"))
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "")

if not DASHBOARD_PASSWORD:
    raise RuntimeError("Set DASHBOARD_PASSWORD in your hosting environment.")
if len(DASHBOARD_PASSWORD) < 12:
    raise RuntimeError("DASHBOARD_PASSWORD must be at least 12 characters.")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError("Set FLASK_SECRET_KEY to a random value of at least 32 characters.")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") == "1",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
    MAX_CONTENT_LENGTH=16 * 1024,
)

def get_db():
    if "db" not in g:
        DATABASE.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'Computer',
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            last_seen TEXT
        );
        CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE SET NULL
        );
    """)
    db.commit()

@app.before_request
def security_headers():
    # Initialize the database lazily for each request.
    if request.endpoint not in {"static"}:
        init_db()

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
    return response

def csrf_token():
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token

app.jinja_env.globals["csrf_token"] = csrf_token

@app.before_request
def verify_csrf():
    if request.method == "POST":
        expected = session.get("_csrf", "")
        supplied = request.form.get("_csrf", "")
        if not expected or not hmac.compare_digest(expected, supplied):
            abort(400, "Invalid form token. Refresh the page and try again.")

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

@app.get("/")
def index():
    return redirect(url_for("dashboard") if session.get("authenticated") else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        supplied = request.form.get("password", "")
        if hmac.compare_digest(supplied, DASHBOARD_PASSWORD):
            session.clear()
            session["authenticated"] = True
            session.permanent = True
            flash("Welcome back.", "success")
            return redirect(url_for("dashboard"))
        flash("Incorrect password.", "error")
    return render_template("login.html")

@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/dashboard")
@login_required
def dashboard():
    db = get_db()
    devices = db.execute("SELECT * FROM devices ORDER BY id DESC").fetchall()
    activity = db.execute("""
        SELECT activity.*, devices.name AS device_name
        FROM activity LEFT JOIN devices ON devices.id = activity.device_id
        ORDER BY activity.id DESC LIMIT 12
    """).fetchall()
    total = db.execute("SELECT COUNT(*) FROM devices").fetchone()[0]
    recent = db.execute("SELECT COUNT(*) FROM devices WHERE last_seen >= datetime('now', '-1 day')").fetchone()[0]
    return render_template("dashboard.html", devices=devices, activity=activity, total=total, recent=recent)

@app.post("/devices/add")
@login_required
def add_device():
    name = request.form.get("name", "").strip()[:60]
    kind = request.form.get("kind", "Computer").strip()[:30]
    description = request.form.get("description", "").strip()[:120]
    if not name:
        flash("Enter a device name.", "error")
        return redirect(url_for("dashboard"))
    db = get_db()
    cur = db.execute(
        "INSERT INTO devices (name, kind, description, created_at) VALUES (?, ?, ?, ?)",
        (name, kind or "Computer", description, now()),
    )
    db.execute("INSERT INTO activity (device_id, message, created_at) VALUES (?, ?, ?)",
               (cur.lastrowid, "Device added manually", now()))
    db.commit()
    flash("Device added.", "success")
    return redirect(url_for("dashboard"))

@app.post("/devices/<int:device_id>/check-in")
@login_required
def check_in(device_id):
    db = get_db()
    device = db.execute("SELECT id FROM devices WHERE id = ?", (device_id,)).fetchone()
    if device is None:
        abort(404)
    timestamp = now()
    db.execute("UPDATE devices SET last_seen = ? WHERE id = ?", (timestamp, device_id))
    db.execute("INSERT INTO activity (device_id, message, created_at) VALUES (?, ?, ?)",
               (device_id, "Manual check-in recorded from dashboard", timestamp))
    db.commit()
    flash("Check-in recorded.", "success")
    return redirect(url_for("dashboard"))

@app.post("/devices/<int:device_id>/delete")
@login_required
def delete_device(device_id):
    db = get_db()
    db.execute("DELETE FROM devices WHERE id = ?", (device_id,))
    db.commit()
    flash("Device removed.", "success")
    return redirect(url_for("dashboard"))

@app.post("/activity/add")
@login_required
def add_activity():
    message = request.form.get("message", "").strip()[:240]
    if not message:
        flash("Write a message first.", "error")
        return redirect(url_for("dashboard"))
    db = get_db()
    db.execute("INSERT INTO activity (message, created_at) VALUES (?, ?)", (message, now()))
    db.commit()
    flash("Note added to activity.", "success")
    return redirect(url_for("dashboard"))

@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", code=400, message=getattr(error, "description", "Bad request")), 400

@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="That page or device could not be found."), 404

if __name__ == "__main__":
    # Local development only. Use a production WSGI server when deployed.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
