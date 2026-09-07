import importlib

import pytest

from core.db_utils import should_use_select_for_update


def test_sqlite_default_db_should_not_use_row_locks():
    assert should_use_select_for_update("default") is False


def test_postgres_database_should_use_row_locks():
    assert should_use_select_for_update("remota") is True


def test_secret_key_is_required_in_production(monkeypatch):
    monkeypatch.setenv("DJANGO_ENV", "production")
    monkeypatch.setenv(
        "SECRET_KEY",
        "cambia-esto-por-una-clave-aleatoria-de-50-caracteres",
    )

    import core.settings.base as settings_module

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        importlib.reload(settings_module)
