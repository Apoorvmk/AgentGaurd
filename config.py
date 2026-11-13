from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).resolve().parent
COMPANY_DIR = BASE_DIR / "company"
RESULTS_DIR = BASE_DIR / "results"

# Gateway
GATEWAY_BACKEND = "centralized"

# Database
LOG_DB = RESULTS_DIR / "agentguard_logs.db"
COMPANY_DB = COMPANY_DIR / "acmecorp.db"

# Security
RISK_THRESHOLDS = {
    "medium": 30,
    "high": 60,
    "extreme": 90
}

# Rate limiting
DEFAULT_RATE_LIMIT = 20
RATE_LIMIT_WINDOW = 60

# Approval
APPROVAL_TIMEOUT = 120

# Benchmark
TOOL_LATENCY_MS = 50
SEED = 42