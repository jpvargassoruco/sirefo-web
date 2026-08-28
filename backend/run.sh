#!/usr/bin/env bash
# Levanta el backend SIREFO Web: crea el venv si falta, instala dependencias
# y arranca uvicorn.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "Creando entorno virtual en .venv ..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
