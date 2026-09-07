import pytest
from django.test import TestCase

# Habilitar todas las bases de datos definidas ('default', 'local', 'remota') para las pruebas de Django
TestCase.databases = "__all__"

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db, transactional_db):
    pass
