"""登录失败限流：按账号维度锁定，IP 维度默认停用。

存储为进程内内存字典，不引入数据库表结构变更。多进程/多实例部署时
每个进程各自持有计数，属于已知限制；如需全局一致应改为 Redis 等共享存储。

## 为什么默认停用 IP 维度（2026-10-06）

公司约 500 人共用同一办公网出口 IP。IP 维度阈值（10 分钟 30 次）对
「全公司共用一个出口」的场景会误伤：任一员工输错密码都会消耗共享配额，
随后所有人——包括完全没做错任何事的人——都会收到
「登录尝试过于频繁，请稍后再试」。压测复现：单 IP 300 次登录尝试
触发 274 个 429。

账号维度（5 次/300 秒/锁 900 秒）已能防住针对单一账号的暴力破解，
且不会影响他人，因此保留为默认防护。IP 维度改为**可选开关**：
若将来需要防范批量枚举账号，可设环境变量 LOGIN_IP_LIMIT_ENABLED=true 重新启用。
"""

import os
import threading
import time

# 账号维度：5 分钟内失败 5 次，锁定 15 分钟
ACCOUNT_MAX_FAILURES = 5
ACCOUNT_WINDOW_SECONDS = 300
ACCOUNT_LOCK_SECONDS = 900

# IP 维度：默认停用。启用时为 10 分钟内最多 30 次登录尝试。
# 启用前须确认部署环境的出口 IP 不是全公司共用，否则会误伤正常用户。
IP_LIMIT_ENABLED = os.getenv("LOGIN_IP_LIMIT_ENABLED", "false").lower() in ("1", "true", "yes")
IP_MAX_ATTEMPTS = 30
IP_WINDOW_SECONDS = 600

_lock = threading.Lock()
_account_failures: dict[str, list[float]] = {}
_account_locked_until: dict[str, float] = {}
_ip_attempts: dict[str, list[float]] = {}


def _prune(timestamps: list[float], window: float, now: float) -> list[float]:
    return [t for t in timestamps if now - t < window]


def is_account_locked(username: str) -> int:
    """账号是否处于锁定期；返回剩余秒数，未锁定返回 0。

    注意：仅当该账号确实存在锁定记录且已到期时才清理计数，
    否则会把尚未触发锁定的失败计数误删，导致永远不会锁定。
    """
    key = username.strip().lower()
    now = time.monotonic()
    with _lock:
        locked_until = _account_locked_until.get(key)
        if locked_until is None:
            return 0
        if locked_until <= now:
            _account_locked_until.pop(key, None)
            _account_failures.pop(key, None)
            return 0
        return int(locked_until - now) + 1


def is_ip_blocked(ip: str) -> bool:
    """该来源 IP 在窗口内是否已超过尝试上限。

    IP 维度默认停用（IP_LIMIT_ENABLED=False），此时恒返回 False，
    不会产生任何拦截与计数开销。
    """
    if not IP_LIMIT_ENABLED or not ip:
        return False
    now = time.monotonic()
    with _lock:
        attempts = _prune(_ip_attempts.get(ip, []), IP_WINDOW_SECONDS, now)
        _ip_attempts[ip] = attempts
        return len(attempts) >= IP_MAX_ATTEMPTS


def register_ip_attempt(ip: str) -> None:
    """记录一次登录尝试（无论成功失败都计数）。

    IP 维度默认停用时直接返回，不产生任何状态。
    """
    if not IP_LIMIT_ENABLED or not ip:
        return
    now = time.monotonic()
    with _lock:
        attempts = _prune(_ip_attempts.get(ip, []), IP_WINDOW_SECONDS, now)
        attempts.append(now)
        _ip_attempts[ip] = attempts


def register_failure(username: str) -> None:
    """记录一次登录失败；达到阈值后锁定该账号。"""
    key = username.strip().lower()
    if not key:
        return
    now = time.monotonic()
    with _lock:
        failures = _prune(_account_failures.get(key, []), ACCOUNT_WINDOW_SECONDS, now)
        failures.append(now)
        if len(failures) >= ACCOUNT_MAX_FAILURES:
            # 锁定窗口内保留计数，不再追加；到期后由 is_account_locked 清理。
            _account_locked_until[key] = now + ACCOUNT_LOCK_SECONDS
        else:
            _account_failures[key] = failures


def reset_account(username: str) -> None:
    """登录成功后清除该账号的失败计数与锁定。"""
    key = username.strip().lower()
    with _lock:
        _account_failures.pop(key, None)
        _account_locked_until.pop(key, None)