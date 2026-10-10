import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 backend/.env（仅补充未在系统环境中定义的变量）
# python-dotenv 默认 override=False，**系统环境变量优先级更高**。
# 生产环境建议直接用系统环境变量（或 systemd EnvironmentFile），不依赖 .env 文件。
load_dotenv(Path(__file__).resolve().parent / ".env")

# ==================== 数据库配置 ====================
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "123456")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "sales_data")

# 注意：不要再用字符串拼接生成 DATABASE_URL。库名可能是中文（如「东南亚运营数据」），
# 拼接后若被拿去建Engine 会因编码问题出错。连接串统一由 database.URL.create() 构造。

# ==================== 连接池配置（针对多人并发） ====================
# pool_size 可创建的常驻连接数；max_overflow 超过上限后临时再开的最大连接数
# pool_recycle 连接超过该秒数后回收，避免 MySQL wait_timeout 断连
POOL_SIZE = int(os.getenv("POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("MAX_OVERFLOW", "20"))
POOL_RECYCLE = int(os.getenv("POOL_RECYCLE", "3600"))
POOL_PRE_PING = True

# ==================== 认证配置 ====================
# 已知的弱/公开密钥：命中即拒绝启动，避免伪造任意角色 Token。
INSECURE_SECRET_KEYS = {
    "please-change-this-in-production",
    "secret",
    "changeme",
}
SECRET_KEY = os.getenv("SECRET_KEY", "")
MIN_SECRET_KEY_LENGTH = 32

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY 未配置。复制 backend/.env.example 为 backend/.env 并填入强随机密钥，"
        "可用 python -c \"import secrets; print(secrets.token_urlsafe(48))\" 生成。"
    )
if SECRET_KEY in INSECURE_SECRET_KEYS or len(SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
    raise RuntimeError(
        f"SECRET_KEY 过弱（长度 {len(SECRET_KEY)}，要求至少 {MIN_SECRET_KEY_LENGTH} 且不得为默认值）。"
        "请生成新的强密钥：python -c \"import secrets; print(secrets.token_urlsafe(48))\"。"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))  # 30 天

# ==================== 服务启动配置 ====================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
