from sqlalchemy import create_engine, text, URL
from sqlalchemy.engine import Engine

import config

# 用 URL.create 构造，自动处理中文库名/特殊字符，避免字符串拼接的编码坑
DATABASE_URL = URL.create(
    "mysql+pymysql",
    username=config.DB_USER,
    password=config.DB_PASS,
    host=config.DB_HOST,
    port=config.DB_PORT,
    database=config.DB_NAME,
    query={"charset": "utf8mb4"},
)

engine: Engine = create_engine(
    DATABASE_URL,
    pool_size=config.POOL_SIZE,
    max_overflow=config.MAX_OVERFLOW,
    pool_recycle=config.POOL_RECYCLE,
    pool_pre_ping=config.POOL_PRE_PING,
    echo=False,
)


def run_query(sql_str: str, params: dict | None = None) -> list[dict]:
    """统一执行只读查询，返回 list[dict]（可直接被 FastAPI JSON 序列化）。"""
    with engine.connect() as conn:
        rows = conn.execute(text(sql_str), params or {}).mappings().all()
    return [dict(row) for row in rows]


def run_execute(sql_str: str, params: dict | None = None) -> int:
    """Execute a write statement in a transaction and return affected rows."""
    with engine.begin() as conn:
        result = conn.execute(text(sql_str), params or {})
    return result.rowcount


def init_business_tables() -> None:
    """Create the audit table; report tables already belong to the business schema."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS operation_security_audit (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(100) NULL,
            action VARCHAR(100) NOT NULL,
            detail VARCHAR(500) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            KEY idx_audit_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """,
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
