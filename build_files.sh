#!/bin/bash

# Ensure pip is up-to-date
pip install --upgrade pip

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Collect static files (without prompting for user input)
python manage.py collectstatic --noinput
