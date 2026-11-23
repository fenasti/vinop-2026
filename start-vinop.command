#!/bin/bash
# VinOp 2026: set up (first time only) and start the local server.
# Double-click this file in Finder, or run ./start-vinop.command
cd "$(dirname "$0")" || exit 1

PY=""
for p in python3.14 python3.13 python3.12 python3; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
    PY="$p"; break
  fi
done
if [ -z "$PY" ]; then
  echo "❌ Necesitas Python 3.12 o más nuevo. Tienes: $(python3 --version 2>&1)"
  echo "   Instálalo desde https://www.python.org/downloads/ y vuelve a abrir este archivo."
  read -r -p "Pulsa Enter para cerrar…"; exit 1
fi
echo "✅ Usando $($PY --version)"

if [ ! -x .venv/bin/python ]; then
  echo "→ Creando el entorno virtual (.venv)…"
  "$PY" -m venv .venv || { read -r -p "Error. Enter para cerrar…"; exit 1; }
fi
source .venv/bin/activate

echo "→ Instalando dependencias…"
pip install -q --upgrade pip
pip install -q -r requirements.txt || { read -r -p "Error instalando. Enter para cerrar…"; exit 1; }

echo "→ Preparando la base de datos…"
python manage.py migrate --noinput
python manage.py seed_demo

if ! python manage.py shell -c "from django.contrib.auth import get_user_model as g; import sys; sys.exit(0 if g().objects.filter(is_superuser=True).exists() else 1)"; then
  echo ""
  echo "👤 Crea tu cuenta de dueño (usa tu email; la contraseña no se ve al escribir):"
  python manage.py createsuperuser
fi

PORT=$(python -c "
import socket
for port in range(8000, 8011):
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1', port)) != 0:
            print(port); break
")
echo ""
echo "🍷 VinOp corriendo en http://127.0.0.1:$PORT  (Ctrl+C para pararlo)"
python manage.py runserver "127.0.0.1:$PORT"
