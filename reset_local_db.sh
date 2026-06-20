#!/bin/bash
# Wipes the local SQLite database and recreates an empty schema.
# Does NOT touch production (Turso) — local only.
set -e

cd "$(dirname "$0")"
source venv/bin/activate

rm -f elp.db
python -c "from database import Base, engine; Base.metadata.create_all(bind=engine); print('Fresh local DB created.')"
