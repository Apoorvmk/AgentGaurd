"""Fail-closed tool execution behind the AgentGuard policy engine."""
from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

from company.db_tools import read_record
from gateway.approval import request_approval, send_alert
from gateway.engine import check_request

logger = logging.getLogger(__name__)


def _read_db(args: dict[str, Any]) -> Any:
    table, record_id = args.get("table"), args.get("id")
    if not isinstance(table, str) or not table.replace("_", "").isalnum():
        raise ValueError("Invalid table")
    if isinstance(record_id, bool) or not isinstance(record_id, int) or record_id <= 0:
        raise ValueError("Invalid record id")
    return read_record(table, record_id)


def _read_file(args: dict[str, Any], allowed_dirs: list[str]) -> str:
    raw_path = args.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("Invalid file path")
    requested = Path(raw_path).resolve(strict=True)
    if not requested.is_file():
        raise ValueError("Path is not a file")
    roots = [Path(root).resolve(strict=True) for root in allowed_dirs]
    if not any(requested.is_relative_to(root) for root in roots):
        raise PermissionError("File path not allowed")
    return requested.read_text(encoding="utf-8")


def _send_payment(args: dict[str, Any]) -> dict[str, Any]:
    amount, recipient = args.get("amount"), args.get("to")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount <= 0:
        raise ValueError("Invalid payment amount")
    if not isinstance(recipient, str) or not recipient.strip():
        raise ValueError("Invalid payment recipient")
    return {"status": "simulated", "amount": amount, "to": recipient.strip()}


def _send_email(args: dict[str, Any]) -> dict[str, Any]:
    recipient, subject, body = args.get("to"), args.get("subject"), args.get("body")
    if not isinstance(recipient, str) or "@" not in recipient:
        raise ValueError("Invalid email recipient")
    if not isinstance(subject, str) or not isinstance(body, str):
        raise ValueError("Invalid email content")
    return {"status": "simulated", "to": recipient, "subject": subject}


def _browse(args: dict[str, Any]) -> dict[str, Any]:
    url = args.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValueError("Invalid URL")
    # Deliberately no network access; this is a local simulated service.
    return {"status": "simulated", "url": url, "content": "Browsing is simulated."}


def execute_tool(agent_id: str, tool: str, args: dict, run_id: str) -> dict[str, Any]:
    """Authorize and execute a supported tool, returning only sanitized errors."""
    if tool not in {"read_db", "read_file", "send_payment", "send_email", "browse"}:
        try:
            check_request(agent_id, tool, args, run_id)
        except Exception:
            logger.exception("Authorization check failed for unknown tool")
        return {"success": False, "decision": "block", "result": None, "error": "Unknown tool"}
    authorization_args = args
    if tool == "send_email" and isinstance(args, dict):
        authorization_args = dict(args)
        recipient = authorization_args.get("to")
        if isinstance(recipient, str) and "@" in recipient:
            authorization_args["domain"] = recipient.rsplit("@", 1)[1].lower()
    try:
        decision = check_request(agent_id, tool, authorization_args, run_id)
    except Exception:
        logger.exception("Authorization check failed for tool %s", tool)
        return {"success": False, "decision": "block", "result": None, "error": "Authorization failed"}
    if decision not in {"allow", "alert", "ask_user"}:
        return {"success": False, "decision": "block", "result": None, "error": "Request denied"}
    if decision == "ask_user":
        try:
            if request_approval(agent_id, tool, args) != "approved":
                return {"success": False, "decision": "ask_user", "result": None, "error": "Approval denied"}
        except Exception:
            logger.exception("Approval failed for tool %s", tool)
            return {"success": False, "decision": "ask_user", "result": None, "error": "Approval unavailable; request denied"}
    try:
        if decision == "alert":
            send_alert(agent_id, tool, "Policy requires a security alert", "medium")
        if tool == "read_file":
            # Policy paths are the explicit allowlist already checked by check_request.
            from gateway.engine import get_policy
            result = _read_file(args, get_policy(agent_id, tool).get("paths", []))
        else:
            result = {
                "read_db": _read_db,
                "send_payment": _send_payment,
                "send_email": _send_email,
                "browse": _browse,
            }[tool](args)
        return {"success": True, "decision": decision, "result": result, "error": None}
    except Exception:
        logger.exception("Tool execution failed for tool %s", tool)
        return {"success": False, "decision": decision, "result": None, "error": "Tool execution failed"}
