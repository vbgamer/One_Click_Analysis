"""
PythonAnywhere WSGI entry point for the FastAPI backend.

Use this from the PythonAnywhere Web tab WSGI file:

    import sys
    project_home = "/home/YOUR_USERNAME/Anal/backend"
    if project_home not in sys.path:
        sys.path.insert(0, project_home)

    from pythonanywhere_wsgi import application
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from a2wsgi import ASGIMiddleware


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

# Safe default for PythonAnywhere free tier. Replace with Postgres only on paid
# PythonAnywhere or if using PythonAnywhere-hosted Postgres.
os.environ.setdefault("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'sql_app.db'}")

from main import app  # noqa: E402


application = ASGIMiddleware(app)
