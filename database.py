import os
import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

pools = {}

def get_connection(database: str):
    allowed = {"agentguard_logs", "acmecorp"}

    if database not in allowed:
        raise ValueError("Invalid database")

    if database not in pools:
        pools[database] = pooling.MySQLConnectionPool(
            pool_name=f"{database}_pool",
            pool_size=20,
            **DB_CONFIG,
            database=database
        )

    return pools[database].get_connection()