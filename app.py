import hmac
import os

from flask import Flask, redirect, render_template_string, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD")

if not app.secret_key or not DASHBOARD_PASSWORD:
    raise RuntimeError(
        "Set FLASK_SECRET_KEY and DASHBOARD_PASSWORD environment variables before starting."
    )

LOGIN_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sign in</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; display: grid; place-items: center;
      background: #0b1020; color: #edf2ff; font: 16px system-ui, sans-serif; }
    main { width: min(92vw, 390px); padding: 32px; border: 1px solid #27324b;
      border-radius: 18px; background: #121a2e; box-shadow: 0 20px 60px #0006; }
    h1 { margin-top: 0; font-size: 1.6rem; }
    p { color: #aab6d3; }
    input, button { width: 100%; padding: 13px 14px; border-radius: 10px;
      font: inherit; }
    input { margin: 12px 0; border: 1px solid #394866; background: #0b1020; color: white; }
    button { border: 0; background: #6d8cff; color: #081020; font-weight: 700; cursor: pointer; }
    .error { color: #ff9caa; }
  </style>
</head>
<body>
  <main>
    <h1>Dashboard login</h1>
    <p>Enter the dashboard password to continue.</p>
    {% if error %}<p class="error">{{ error }}</p>{% endif %}
    <form method="post">
      <label for="password">Password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" required autofocus>
      <button type="submit">Enter dashboard</button>
    </form>
  </main>
</body>
</html>
"""

DASHBOARD_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Main dashboard</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; background: #0b1020; color: #edf2ff;
      font: 16px system-ui, sans-serif; }
    header { display: flex; justify-content: space-between; align-items: center;
      gap: 16px; padding: 22px 5vw; border-bottom: 1px solid #27324b; }
    h1 { margin: 0; font-size: 1.5rem; }
    a { color: #a9bcff; }
    main { padding: 5vw; }
    .empty { padding: 28px; border: 1px solid #27324b; border-radius: 16px;
      background: #121a2e; color: #aab6d3; }
    button { border: 1px solid #53658c; border-radius: 9px; padding: 9px 14px;
      background: #1b2945; color: white; cursor: pointer; }
  </style>
</head>
<body>
  <header>
    <h1>Main dashboard</h1>
    <form method="post" action="{{ url_for('logout') }}">
      <button type="submit">Log out</button>
    </form>
  </header>
  <main>
    <section class="empty">
      <h2>Welcome</h2>
      <p>Your dashboard is ready. You can add your own dashboard content here later.</p>
    </section>
  </main>
</body>
</html>
"""

@app.after_request
def secure_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        submitted = request.form.get("password", "")
        if hmac.compare_digest(submitted, DASHBOARD_PASSWORD):
            session.clear()
            session["authenticated"] = True
            return redirect(url_for("dashboard"))
        error = "Incorrect password. Please try again."

    return render_template_string(LOGIN_PAGE, error=error)


@app.get("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return render_template_string(DASHBOARD_PAGE)


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
