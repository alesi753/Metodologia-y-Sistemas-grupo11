#!/usr/bin/env bash
# Levanta el aula virtual en Linux y macOS. Prepara Python con uv y deja el
# resto (clave de IA, base y servidor) a scripts/iniciar.py.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
    echo 'Instalando uv, que prepara Python automáticamente...'
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

[ -x .venv/bin/python ] || uv venv --quiet --python '>=3.12' .venv
uv pip install --quiet --python .venv/bin/python -r requirements.txt
exec .venv/bin/python scripts/iniciar.py
