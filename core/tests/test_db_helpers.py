from core.db_utils import should_use_select_for_update


def test_sqlite_default_db_should_not_use_row_locks():
    assert should_use_select_for_update("default") is False


def test_postgres_database_should_use_row_locks():
    assert should_use_select_for_update("remota") is True
