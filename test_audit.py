from gateway import audit


class FakeCursor:
    def execute(self, query, params):
        self.query = query
        self.params = params

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.fake_cursor = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def close(self):
        pass


def test_audit_insert_uses_bound_parameters(monkeypatch):
    conn = FakeConnection()
    monkeypatch.setattr(audit, "get_connection", lambda db: conn)
    audit.log_decision("run", "agent", "read_db", {"table": "customers"}, "allow")
    assert conn.committed
    assert conn.fake_cursor.params[0:5] == ("run", "agent", "read_db", '{"table": "customers"}', "allow")
