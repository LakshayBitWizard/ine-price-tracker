#!/usr/bin/env bash
# Exit on error
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt
export PLAYWRIGHT_BROWSERS_PATH=0
python -m playwright install chromium
python manage.py collectstatic --no-input
