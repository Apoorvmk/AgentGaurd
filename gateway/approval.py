
from datetime import datetime


def request_approval(agent_id, tool, args):

    print("\n--- APPROVAL REQUIRED ---")
    print(f"Agent: {agent_id}")
    print(f"Tool: {tool}")
    print(f"Arguments: {args}")

    while True:
        choice = input("Approve? (y/n): ").strip().lower()

        if choice == "y":
            return "approved"

        if choice == "n":
            return "denied"


def send_alert(agent_id, tool, reason, severity):

    print("\n========== SECURITY ALERT ==========")
    print(f"Time: {datetime.now()}")
    print(f"Agent: {agent_id}")
    print(f"Tool: {tool}")
    print(f"Severity: {severity}")
    print(f"Reason: {reason}")
    print("===================================")
