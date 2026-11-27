#!/usr/bin/env python
"""Compatibilidad con el antiguo script populate_db.py.

La carga oficial e idempotente está en ``manage.py poblar_demo`` y por defecto
escribe en SQLite local. Este archivo mantiene el comando histórico sin volver
a crear registros aleatorios ni saltarse las validaciones de los modelos.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

import django

django.setup()

from django.core.management import call_command


if __name__ == "__main__":
    call_command("poblar_demo", database="local", verbosity=1)
