"""One-time initial schema preparation. Commit generated migrations before deployment.
Does not apply database migrations, contact payment providers, or create users.
"""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app"
with tempfile.TemporaryDirectory(prefix="marketplace-schema-") as tmp:
    env = os.environ.copy()
    env.update(DEBUG="1", TESTING="1", PAYMENTS_MODE="disabled",
               DATABASE_URL="sqlite:///" + (Path(tmp) / "schema.sqlite3").as_posix())
    manage = [sys.executable, str(APP / "manage.py")]
    subprocess.run(manage + ["makemigrations", "market", "--noinput"], cwd=APP, env=env, check=True)
    subprocess.run(manage + ["makemigrations", "market", "--check", "--dry-run"], cwd=APP, env=env, check=True)
print("Schema prepared. Commit app/market/migrations/*.py before deployment.")
print("No migrations applied; no payments or users created.")
