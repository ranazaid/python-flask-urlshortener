"""Flask URL shortener.

Routes:
    GET  /                 HTML form + list of recent links
    POST /api/shorten      JSON {"url": "..."} -> {"code", "short_url"}
    GET  /<code>           302 redirect to the original URL (counts the click)
    GET  /api/stats/<code> JSON click stats for a code
"""
from __future__ import annotations

import secrets
import sqlite3
import string
from urllib.parse import urlparse

from flask import Flask, abort, g, jsonify, redirect, render_template_string, request, url_for

DATABASE = "links.db"
ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6

app = Flask(__name__)


# --- database helpers -------------------------------------------------------

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config.get("DATABASE", DATABASE))
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    get_db().execute(
        """
        CREATE TABLE IF NOT EXISTS links (
            code       TEXT PRIMARY KEY,
            url        TEXT NOT NULL,
            clicks     INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    get_db().commit()


with app.app_context():
    init_db()


# --- core logic -------------------------------------------------------------

def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def create_link(url: str) -> str:
    db = get_db()
    # Reuse an existing code for the same URL instead of creating duplicates.
    row = db.execute("SELECT code FROM links WHERE url = ?", (url,)).fetchone()
    if row:
        return row["code"]
    while True:
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        try:
            db.execute("INSERT INTO links (code, url) VALUES (?, ?)", (code, url))
            db.commit()
            return code
        except sqlite3.IntegrityError:
            continue  # extremely rare collision — try another code


# --- routes -----------------------------------------------------------------

PAGE = """
<!doctype html>
<title>Shortener</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
  input[type=url] { width: 70%; padding: 8px; } button { padding: 8px 14px; }
  table { width: 100%; border-collapse: collapse; margin-top: 24px; }
  td, th { text-align: left; padding: 6px; border-bottom: 1px solid #ddd; font-size: 14px; }
  .err { color: #b00020; }
</style>
<h1>URL Shortener</h1>
<form method="post" action="{{ url_for('shorten_form') }}">
  <input type="url" name="url" placeholder="https://example.com/very/long/path" required>
  <button>Shorten</button>
</form>
{% if error %}<p class="err">{{ error }}</p>{% endif %}
{% if short %}<p>Short link: <a href="{{ short }}">{{ short }}</a></p>{% endif %}
<table>
  <tr><th>Code</th><th>URL</th><th>Clicks</th></tr>
  {% for l in links %}
  <tr><td><a href="{{ url_for('follow', code=l.code) }}">{{ l.code }}</a></td>
      <td>{{ l.url }}</td><td>{{ l.clicks }}</td></tr>
  {% endfor %}
</table>
"""


def recent_links():
    return get_db().execute(
        "SELECT code, url, clicks FROM links ORDER BY created_at DESC LIMIT 20"
    ).fetchall()


@app.get("/")
def index():
    return render_template_string(PAGE, links=recent_links(), short=None, error=None)


@app.post("/")
def shorten_form():
    url = request.form.get("url", "").strip()
    if not is_valid_url(url):
        return render_template_string(
            PAGE, links=recent_links(), short=None, error="Please enter a valid http(s) URL."
        ), 400
    code = create_link(url)
    short = url_for("follow", code=code, _external=True)
    return render_template_string(PAGE, links=recent_links(), short=short, error=None)


@app.post("/api/shorten")
def shorten_api():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url", "")).strip()
    if not is_valid_url(url):
        return jsonify(error="Field 'url' must be a valid http(s) URL."), 400
    code = create_link(url)
    return jsonify(code=code, short_url=url_for("follow", code=code, _external=True)), 201


@app.get("/api/stats/<code>")
def stats(code: str):
    row = get_db().execute(
        "SELECT code, url, clicks, created_at FROM links WHERE code = ?", (code,)
    ).fetchone()
    if row is None:
        return jsonify(error="Not found"), 404
    return jsonify(dict(row))


@app.get("/<code>")
def follow(code: str):
    db = get_db()
    row = db.execute("SELECT url FROM links WHERE code = ?", (code,)).fetchone()
    if row is None:
        abort(404)
    db.execute("UPDATE links SET clicks = clicks + 1 WHERE code = ?", (code,))
    db.commit()
    return redirect(row["url"], code=302)


if __name__ == "__main__":
    app.run(debug=True)
