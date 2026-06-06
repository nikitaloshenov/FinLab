#!/bin/sh
set -eu

python - <<'PY'
import os
import socket
import time

host = os.getenv("POSTGRES_HOST", "postgres")
port = int(os.getenv("POSTGRES_PORT", "5432"))
deadline = time.time() + 60

while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            print("PostgreSQL is ready")
            break
    except OSError:
        if time.time() >= deadline:
            raise SystemExit("PostgreSQL readiness check timed out")
        print("Waiting for PostgreSQL...")
        time.sleep(2)
PY

python -m alembic upgrade head
python scripts/import_key_rate_decisions.py --file app/data/key_rate_decisions_official.csv
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
