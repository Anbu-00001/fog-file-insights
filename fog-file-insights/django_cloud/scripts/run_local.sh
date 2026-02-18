#!/bin/bash
# run inside django_cloud folder with virtualenv active
export DJANGO_DEBUG=True
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
