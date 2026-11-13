
import json
import math
import time
from pathlib import Path
from collections import defaultdict, deque
from threading import Lock

import yaml

from database import get_connection
from gateway.audit import log_decision

# Configuration
MATRIX_PATH = Path(__file__).resolve().parent.parent / "matrix.yaml"

VALID_TIERS = {"allow", "alert", "ask_user", "block"}

RATE_LIMIT = 20
WINDOW_SECONDS = 60

requests = defaultdict(deque)
rate_lock = Lock()


# Load agent permissions
def get_policy(agent_id, tool):
    with open(MATRIX_PATH, "r") as file:
        matrix = yaml.safe_load(file) or {}

    policy = matrix.get(agent_id, {}).get(tool)

    if not isinstance(policy, dict):
        return {"tier": "block"}

    if policy.get("tier") not in VALID_TIERS:
        return {"tier": "block"}

    return policy


# Rate limiting
def check_rate_limit(agent_id):
    now = time.monotonic()

    with rate_lock:
        history = requests[agent_id]

        while history and now - history[0] >= WINDOW_SECONDS:
            history.popleft()

        if len(history) >= RATE_LIMIT:
            return False

        history.append(now)
        return True


# Argument validation
def validate_args(tool, args, policy):

    if not isinstance(args, dict):
        return False, "Invalid arguments"

    if tool == "read_db":
        if args.get("table") not in policy.get("tables", []):
            return False, "Table not allowed"

    elif tool == "send_payment":
        amount = args.get("amount")

        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            return False, "Invalid payment amount"

        if not math.isfinite(amount) or amount <= 0:
            return False, "Invalid payment amount"

        if amount > policy.get("max_amount", 0):
            return False, "Payment limit exceeded"

    elif tool == "send_email":
        domain = args.get("domain")

        if not isinstance(domain, str):
            return False, "Invalid email domain"

        if domain.lower() not in policy.get("domains", []):
            return False, "Email domain not allowed"

    elif tool == "read_file":
        try:
            path = Path(args.get("path", "")).resolve()
            allowed = [
                Path(p).resolve()
                for p in policy.get("paths", [])
            ]

            if not any(path.is_relative_to(root) for root in allowed):
                return False, "File path not allowed"

        except (ValueError, OSError):
            return False, "Invalid file path"

    return True, None


# Sequence detection
def check_sequence(agent_id, tool, args, run_id):

    conn = get_connection("agentguard_logs")
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT tool, args, decision
            FROM audit_logs
            WHERE agent_id = %s AND run_id = %s
            ORDER BY id DESC
            LIMIT 20
        """, (agent_id, run_id))

        history = cursor.fetchall()

        for event in history:
            old_args = event["args"]

            if isinstance(old_args, str):
                old_args = json.loads(old_args)

            path = str(old_args.get("path", "")).lower()

            denied_secret_read = (
                event["tool"] == "read_file"
                and event["decision"] == "block"
                and ("secret" in path or ".env" in path)
            )

            if denied_secret_read and tool in {
                "send_payment", "send_email", "browse"
            }:
                return False, "Suspicious action after denied credential access"

        return True, None

    finally:
        cursor.close()
        conn.close()


# Central gateway decision engine
def check_request(agent_id, tool, args, run_id):

    decision = "block"
    reason = "Gateway error"
    severity = "high"

    try:
        policy = get_policy(agent_id, tool)

        if not check_rate_limit(agent_id):
            reason = "Rate limit exceeded"
            raise PermissionError(reason)

        valid, reason = validate_args(tool, args, policy)

        if not valid:
            raise PermissionError(reason)

        valid, reason = check_sequence(
            agent_id, tool, args, run_id
        )

        if not valid:
            raise PermissionError(reason)

        decision = policy.get("tier", "block")

        if decision not in VALID_TIERS:
            decision = "block"

        reason = None
        severity = "low"

    except PermissionError:
        decision = "block"

    except Exception:
        decision = "block"
        reason = "Internal gateway error"

    # Audit logging is mandatory
    try:
        log_decision(
            run_id=run_id,
            agent_id=agent_id,
            tool=tool,
            args=args,
            decision=decision,
            rule_hit=reason,
            severity=severity
        )
    except Exception:
        return "block"

    return decision
