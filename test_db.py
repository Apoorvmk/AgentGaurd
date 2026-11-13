import pytest

import database


def test_connection_rejects_unapproved_database():
    with pytest.raises(ValueError, match="Invalid database"):
        database.get_connection("other")


def test_connection_pool_uses_database_credentials_internally(monkeypatch):
    calls = []

    class Pool:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def get_connection(self):
            return "fake connection"

    monkeypatch.setattr(database.pooling, "MySQLConnectionPool", Pool)
    monkeypatch.setattr(database, "pools", {})
    assert database.get_connection("acmecorp") == "fake connection"
    assert calls[0]["database"] == "acmecorp"
