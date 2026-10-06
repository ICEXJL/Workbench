"""登录限流与角色守卫的安全回归测试。

只验证纯逻辑，不触碰真实业务库；审计写入通过替身验证。
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from services import login_throttle


class LoginThrottleAccountTests(unittest.TestCase):
    def setUp(self) -> None:
        login_throttle._account_failures.clear()
        login_throttle._account_locked_until.clear()
        login_throttle._ip_attempts.clear()

    def test_account_locks_after_threshold_failures(self) -> None:
        username = "case_lock"
        for _ in range(login_throttle.ACCOUNT_MAX_FAILURES - 1):
            self.assertEqual(login_throttle.is_account_locked(username), 0)
            login_throttle.register_failure(username)
        login_throttle.register_failure(username)
        self.assertGreater(login_throttle.is_account_locked(username), 0)

    def test_querying_unlocked_account_does_not_clear_failures(self) -> None:
        """回归：曾因查询时误删计数导致永不锁定。"""
        username = "case_keep"
        login_throttle.register_failure(username)
        login_throttle.register_failure(username)
        login_throttle.is_account_locked(username)
        self.assertEqual(len(login_throttle._account_failures[username]), 2)

    def test_locked_account_reports_remaining_seconds(self) -> None:
        username = "case_remain"
        for _ in range(login_throttle.ACCOUNT_MAX_FAILURES):
            login_throttle.register_failure(username)
        remaining = login_throttle.is_account_locked(username)
        self.assertLessEqual(remaining, login_throttle.ACCOUNT_LOCK_SECONDS)
        self.assertGreater(remaining, login_throttle.ACCOUNT_LOCK_SECONDS - 60)

    def test_success_resets_failures_and_lock(self) -> None:
        username = "case_reset"
        for _ in range(login_throttle.ACCOUNT_MAX_FAILURES):
            login_throttle.register_failure(username)
        self.assertGreater(login_throttle.is_account_locked(username), 0)
        login_throttle.reset_account(username)
        self.assertEqual(login_throttle.is_account_locked(username), 0)

    def test_failures_are_case_insensitive(self) -> None:
        login_throttle.register_failure("MixedCase")
        self.assertIn("mixedcase", login_throttle._account_failures)


class LoginThrottleIpTests(unittest.TestCase):
    """IP 维度自 2026-10-06 起默认停用。

    全公司共用办公网出口 IP 时，IP 阈值会误伤正常用户：
    压测中单 IP 300 次尝试触发 274 个 429。
    停用后需保证既不拦截、也不产生任何状态。
    """

    def setUp(self) -> None:
        login_throttle._ip_attempts.clear()

    def _with_ip_limit(self, enabled: bool):
        """临时切换开关，用完恢复，保证用例之间互不污染。"""
        original = login_throttle.IP_LIMIT_ENABLED
        login_throttle.IP_LIMIT_ENABLED = enabled
        self.addCleanup(setattr, login_throttle, "IP_LIMIT_ENABLED", original)

    def test_ip_limit_disabled_by_default(self) -> None:
        """默认配置下 IP 维度必须处于停用状态。"""
        self.assertFalse(login_throttle.IP_LIMIT_ENABLED)

    def test_disabled_never_blocks_even_above_threshold(self) -> None:
        """停用时：超过阈值也不拦截，且不记录任何计数。"""
        self._with_ip_limit(False)
        ip = "10.0.0.1"
        for _ in range(login_throttle.IP_MAX_ATTEMPTS * 10):
            login_throttle.register_ip_attempt(ip)
        self.assertFalse(login_throttle.is_ip_blocked(ip))
        self.assertNotIn(ip, login_throttle._ip_attempts)

    def test_enabled_still_blocks_after_max_attempts(self) -> None:
        """开关打开时行为不变，保护能力可随时恢复。"""
        self._with_ip_limit(True)
        ip = "10.0.0.1"
        for _ in range(login_throttle.IP_MAX_ATTEMPTS):
            login_throttle.register_ip_attempt(ip)
        self.assertTrue(login_throttle.is_ip_blocked(ip))

    def test_enabled_tracks_different_ips_independently(self) -> None:
        self._with_ip_limit(True)
        for _ in range(login_throttle.IP_MAX_ATTEMPTS):
            login_throttle.register_ip_attempt("10.0.0.2")
        self.assertFalse(login_throttle.is_ip_blocked("10.0.0.3"))

    def test_empty_ip_is_never_blocked(self) -> None:
        for enabled in (True, False):
            self._with_ip_limit(enabled)
            self.assertFalse(login_throttle.is_ip_blocked(""))


if __name__ == "__main__":
    unittest.main()