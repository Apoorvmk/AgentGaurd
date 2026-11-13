import json
from database import get_connection


def log_decision(
    run_id,
    agent_id,
    tool,
    args,
    decision,
    rule_hit=None,
    severity="low"
):
    conn = get_connection("agentguard_logs")
    cursor = conn.cursor()

    try:
        query = """
            INSERT INTO audit_logs
            (run_id, agent_id, tool, args, decision, rule_hit, severity)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (
            run_id,
            agent_id,
            tool,
            json.dumps(args),
            decision,
            rule_hit,
            severity
        ))

        conn.commit()

    finally:
        cursor.close()
        conn.close()