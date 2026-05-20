"""
One Click Analysis - Backend Manager
=====================================
Usage:
    python manage.py runserver            -> Start on default host 0.0.0.0:8000
    python manage.py runserver 8080       -> Start on custom port
    python manage.py runserver 0.0.0.0:9000  -> Start on custom host:port
"""

import sys
import os
import subprocess

# ── Complete package list for this project ────────────────────────────────────
PACKAGES = [
    # Core API
    "uvicorn",
    "fastapi",
    "python-dotenv",
    "sqlalchemy",
    "passlib",
    "python-jose",
    "python-multipart",
    "psycopg2-binary",
    "bcrypt",
    # Data & ML
    "pandas",
    "numpy",
    "scipy",
    "scikit-learn",
    "FLAML",
    "matplotlib",
    "seaborn",
    "ydata-profiling",
    "openpyxl",
    # AI / Insights
    "huggingface_hub",
    "requests",
    "openai",
]

# Map pip install names -> importable module names for detection
IMPORT_MAP = {
    "uvicorn": "uvicorn",
    "fastapi": "fastapi",
    "python-dotenv": "dotenv",
    "sqlalchemy": "sqlalchemy",
    "passlib": "passlib",
    "python-jose": "jose",
    "python-multipart": "multipart",
    "psycopg2-binary": "psycopg2",
    "bcrypt": "bcrypt",
    "pandas": "pandas",
    "numpy": "numpy",
    "scipy": "scipy",
    "scikit-learn": "sklearn",
    "FLAML": "flaml",
    "matplotlib": "matplotlib",
    "seaborn": "seaborn",
    "ydata-profiling": "ydata_profiling",
    "openpyxl": "openpyxl",
    "huggingface_hub": "huggingface_hub",
    "requests": "requests",
    "openai": "openai",
}

# ─────────────────────────────────────────────────────────────────────────────

def ensure_packages():
    """Install any missing packages into the current Python environment."""
    import importlib

    missing = []
    for pkg, mod in IMPORT_MAP.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"\n  [Setup] Missing packages detected: {', '.join(missing)}")
        print("  [Setup] Installing now — this only happens once...\n")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet"] + missing
        )
        print("\n  [Setup] All packages installed successfully!\n")
    else:
        print("  [Setup] All dependencies are satisfied.\n")


def print_banner():
    print("=" * 55)
    print("   One Click Analysis - FastAPI Backend Manager")
    print("=" * 55)


def run_server(host="0.0.0.0", port=8000, reload=True):
    print_banner()
    ensure_packages()

    print(f"  Starting server at  ->  http://{host}:{port}")
    print(f"  API Docs available  ->  http://localhost:{port}/docs")
    print(f"  Auto-reload         ->  {'ON' if reload else 'OFF'}")
    print("\n  Press CTRL+C to stop the server.\n")
    print("-" * 55)

    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", host,
        "--port", str(port),
    ]
    if reload:
        cmd.append("--reload")

    try:
        subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))
    except KeyboardInterrupt:
        print("\n\n  Server stopped. Goodbye!")


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("help", "--help", "-h"):
        print(__doc__)
        return

    command = args[0]

    if command == "runserver":
        host = "0.0.0.0"
        port = 8000

        if len(args) > 1:
            addr = args[1]
            if ":" in addr:
                host, port_str = addr.rsplit(":", 1)
                port = int(port_str)
            else:
                port = int(addr)

        run_server(host=host, port=port)

    else:
        print(f"\n  Unknown command: '{command}'")
        print("  Available commands:  runserver")
        print("\n  Usage: python manage.py runserver [host:port]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
