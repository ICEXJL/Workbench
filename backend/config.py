import os
from pathlib import Path

from dotenv import load_dotenv

# 加载 backend/.env（存在时覆盖环境变量）
load_dotenv(Path(__file__).resolve().parent / ".env")

# ==================== 数据库配置 ====================
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "123456")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "sales_data")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

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
