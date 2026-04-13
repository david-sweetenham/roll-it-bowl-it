import os
import sys


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _resource_dir():
    """Directory containing read-only bundled files (templates, static, schema.sql).

    Development  : directory of this config.py file.
    PyInstaller  : sys._MEIPASS — the temp dir where the bundle is unpacked.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _data_dir():
    """Directory for user-writable data files (the database).

    Development  : same as _resource_dir().
    PyInstaller  : directory of the executable so the DB persists across runs.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# Base dirs
BASE_DIR = _resource_dir()   # read-only resources
DATA_DIR = _data_dir()        # user-writable data

# Database
DB_PATH = os.path.join(DATA_DIR, 'ribi.db')
DB_FILENAME = 'ribi.db'

# Flask
FLASK_HOST = os.environ.get('RIBI_HOST', '127.0.0.1')
FLASK_PORT = _env_int('RIBI_PORT', 5000)
FLASK_DEBUG = _env_bool('RIBI_DEBUG', False)

# Static and template directories
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

# Application
APP_NAME = 'Roll It & Bowl It'
APP_VERSION = '0.1.0-dev'

# Data files
SCHEMA_PATH = os.path.join(BASE_DIR, 'schema.sql')
SEED_DATA_PATH = os.path.join(BASE_DIR, 'seed_data.py')
