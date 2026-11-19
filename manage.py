#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def main():
    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE")
    # Compatibilidad con instalaciones que aún tienen la ruta histórica en
    # una variable de entorno persistente de Windows.
    if settings_module == "core.settings":
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.dev"
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    if len(sys.argv) > 1 and sys.argv[1] == "runserver":
        import django

        django.setup()
        from django.core.management import call_command

        # Migraciones locales obligatorias; la descarga de Neon es opcional y
        # el comando continúa usando SQLite si no hay conexión.
        call_command("preparar_bd_offline", verbosity=0)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django. ¿Activaste el venv?") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
