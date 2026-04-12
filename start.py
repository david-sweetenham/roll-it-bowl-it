# Roll It & Bowl It — start.py
# Development: python start.py --dev
# Production:  python start.py
# Packaged:    built via pyinstaller ribi.spec
"""
start.py — Launch script for Roll It & Bowl It.
Creates ribi.db if it doesn't exist, seeds initial data, then starts Flask.

On Arch/CachyOS: run via  .venv/bin/python start.py
Or use the start.sh / start.bat convenience scripts.
"""

import sys
import os

# If a .venv exists alongside this file and we're not already inside it,
# re-exec using the venv Python so dependencies are available.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_venv_python = os.path.join(BASE_DIR, '.venv', 'bin', 'python')
if (os.path.exists(_venv_python) and
        os.path.abspath(sys.executable) != os.path.abspath(_venv_python)):
    os.execv(_venv_python, [_venv_python] + sys.argv)

# Python version check
if sys.version_info < (3, 10):
    print("ERROR: Python 3.10 or higher is required.")
    print(f"       You are running Python {sys.version}")
    sys.exit(1)

# Flask availability check
try:
    import flask
except ImportError:
    print("Flask not found. Run: pip install flask")
    sys.exit(1)

import sqlite3
import threading
import webbrowser
import time

import config as _cfg
if '--dev' in sys.argv:
    import config_dev as _cfg  # noqa: F811

DB_PATH = _cfg.DB_PATH
SCHEMA_PATH = _cfg.SCHEMA_PATH


def init_db():
    print("Creating database...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    conn.commit()

    import seed_data
    seed_data.seed(conn)
    conn.close()
    print("Database ready.")


def open_browser():
    time.sleep(1.5)
    webbrowser.open(f'http://{_cfg.FLASK_HOST}:{_cfg.FLASK_PORT}')


if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        init_db()
    else:
        print("Database exists — skipping init.")

    # Run schema migrations on every startup (idempotent — safe to re-run)
    import database as _db
    _conn = _db.get_db()
    _db.run_migrations(_conn)
    _db.close_db(_conn)
    print("Migrations: OK.")

    print("=" * 50)
    print("  Roll It & Bowl It: Dice Cricket Done Digitally")
    print(f"  Roll It & Bowl It is running at http://{_cfg.FLASK_HOST}:{_cfg.FLASK_PORT}")
    print("=" * 50)

    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    from app import app
    app.run(host=_cfg.FLASK_HOST, port=_cfg.FLASK_PORT,
            debug=_cfg.FLASK_DEBUG, threaded=True)
