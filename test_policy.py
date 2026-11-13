from gateway.engine import get_policy


def test_configured_policy_is_loaded():
    assert get_policy("hermes_agent", "read_db") == {
        "tables": ["customers", "invoices"],
        "tier": "allow",
    }


def test_unknown_agent_is_blocked():
    assert get_policy("unknown_agent", "read_db") == {"tier": "block"}
