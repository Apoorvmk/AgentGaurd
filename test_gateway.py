from gateway import engine


def test_gateway_blocks_unconfigured_tool(monkeypatch):
    monkeypatch.setattr(engine, "check_rate_limit", lambda agent: True)
    monkeypatch.setattr(engine, "check_sequence", lambda *args: (True, None))
    monkeypatch.setattr(engine, "log_decision", lambda **kwargs: None)
    assert engine.check_request("unknown_agent", "read_db", {"table": "customers", "id": 1}, "run") == "block"


def test_gateway_blocks_disallowed_table(monkeypatch):
    monkeypatch.setattr(engine, "get_policy", lambda *args: {"tier": "allow", "tables": ["customers"]})
    monkeypatch.setattr(engine, "check_rate_limit", lambda agent: True)
    monkeypatch.setattr(engine, "log_decision", lambda **kwargs: None)
    assert engine.check_request("agent", "read_db", {"table": "hr", "id": 1}, "run") == "block"
