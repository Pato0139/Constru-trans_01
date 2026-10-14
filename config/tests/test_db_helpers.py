import importlib

import pytest

from config.db_utils import should_use_select_for_update


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

    import config.settings.base as settings_module

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        importlib.reload(settings_module)


def test_secret_key_is_required_in_development_to_preserve_sessions(monkeypatch, tmp_path):
    import core.settings.base as settings_module

    monkeypatch.setattr(settings_module, "DJANGO_ENV", "development")
    monkeypatch.setattr(settings_module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "env", lambda *_args, **_kwargs: "")

    with pytest.raises(RuntimeError, match="invalida las sesiones"):
        settings_module.get_secret_key()


def test_development_uses_valid_dotenv_key_when_environment_key_is_too_short(
    monkeypatch, tmp_path
):
    import core.settings.base as settings_module

    stable_key = "stable-development-secret-key-with-at-least-32-characters"
    (tmp_path / ".env").write_text(f"SECRET_KEY={stable_key}\n", encoding="utf-8")
    monkeypatch.setattr(settings_module, "BASE_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "DJANGO_ENV", "development")
    monkeypatch.setattr(settings_module, "env", lambda *_args, **_kwargs: "bad")

    assert settings_module.get_secret_key() == stable_key
