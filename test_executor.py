from pathlib import Path

import pytest

from gateway import executor


@pytest.fixture
def setup_gateway(monkeypatch, tmp_path):
    policy = {
        "read_db": {"tier": "allow", "tables": ["customers"]},
        "send_payment": {"tier": "ask_user", "max_amount": 50},
        "read_file": {"tier": "allow", "paths": [str(tmp_path)]},
    }
    monkeypatch.setattr(executor, "request_approval", lambda *args: "approved")
    monkeypatch.setattr(executor, "send_alert", lambda *args: None)
    monkeypatch.setattr("gateway.engine.get_policy", lambda agent, tool: policy.get(tool, {"tier": "block"}))

    def check(agent, tool, args, run):
        p = policy.get(tool)
        if not p:
            return "block"
        if tool == "read_db" and args.get("table") not in p["tables"]:
            return "block"
        if tool == "send_payment" and args.get("amount", 0) > p["max_amount"]:
            return "block"
        return p["tier"]

    monkeypatch.setattr(executor, "check_request", check)
    return tmp_path


def test_authorized_database_read(setup_gateway, monkeypatch):
    monkeypatch.setattr(executor, "read_record", lambda table, ident: {"id": ident, "table": table})
    out = executor.execute_tool("agent", "read_db", {"table": "customers", "id": 1}, "r")
    assert out["success"] and out["result"]["id"] == 1


def test_unauthorized_database_table(setup_gateway, monkeypatch):
    monkeypatch.setattr(executor, "read_record", lambda *args: pytest.fail("executed unauthorized read"))
    out = executor.execute_tool("agent", "read_db", {"table": "hr", "id": 1}, "r")
    assert not out["success"] and out["decision"] == "block"


def test_payment_within_limit_requires_approval(setup_gateway, monkeypatch):
    asked = []
    monkeypatch.setattr(executor, "request_approval", lambda *args: asked.append(args) or "approved")
    out = executor.execute_tool("agent", "send_payment", {"amount": 30, "to": "vendor"}, "r")
    assert out["success"] and out["result"]["status"] == "simulated" and asked


def test_payment_denied_by_user(setup_gateway, monkeypatch):
    executed = []
    monkeypatch.setattr(executor, "request_approval", lambda *args: "denied")
    monkeypatch.setattr(executor, "_send_payment", lambda args: executed.append(args))
    out = executor.execute_tool("agent", "send_payment", {"amount": 30, "to": "vendor"}, "r")
    assert not out["success"] and out["result"] is None
    assert executed == []


def test_payment_approved_by_user(setup_gateway):
    out = executor.execute_tool("agent", "send_payment", {"amount": 30, "to": "vendor"}, "r")
    assert out["success"] and out["decision"] == "ask_user"


def test_payment_exceeding_limit(setup_gateway, monkeypatch):
    executed = []
    monkeypatch.setattr(executor, "request_approval", lambda *args: pytest.fail("approval should not be requested"))
    monkeypatch.setattr(executor, "_send_payment", lambda args: executed.append(args))
    out = executor.execute_tool("agent", "send_payment", {"amount": 51, "to": "vendor"}, "r")
    assert not out["success"] and out["decision"] == "block"
    assert executed == []


def test_unauthorized_file_access(setup_gateway, tmp_path):
    elsewhere = tmp_path.parent / "outside.txt"
    elsewhere.write_text("secret", encoding="utf-8")
    out = executor.execute_tool("agent", "read_file", {"path": str(elsewhere)}, "r")
    assert not out["success"]


def test_path_traversal_attempt(setup_gateway, tmp_path):
    out = executor.execute_tool("agent", "read_file", {"path": str(tmp_path / ".." / "outside.txt")}, "r")
    assert not out["success"]


def test_unknown_tool(setup_gateway):
    out = executor.execute_tool("agent", "shell", {"cmd": "whoami"}, "r")
    assert not out["success"] and out["decision"] == "block"


def test_tool_execution_failure(setup_gateway, monkeypatch):
    monkeypatch.setattr(executor, "read_record", lambda *args: (_ for _ in ()).throw(RuntimeError("secret")))
    out = executor.execute_tool("agent", "read_db", {"table": "customers", "id": 1}, "r")
    assert not out["success"] and out["error"] == "Tool execution failed"
