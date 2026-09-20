#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install --with-deps chromium
python manage.py collectstatic --no-input
