"""安全审计写入：越权拒绝与登录失败事件。

审计写入失败不得影响主业务流程，因此所有异常在此吞掉并记录到标准错误。
"""

import logging
import sys

from database import run_execute

logger = logging.getLogger(__name__)


def record_event(action: str, username: str | None, detail: str | None = None) -> None:
    """向 operation_security_audit 写入一条记录；失败不影响调用方。"""
    try:
        run_execute(
            """INSERT INTO operation_security_audit (username, action, detail)
               VALUES (:username, :action, :detail)""",
            {
                "username": (username or "")[:100] or None,
                "action": action[:100],
                "detail": (detail or "")[:500] or None,
            },
        )
    except Exception as exc:  # noqa: BLE001 - 审计不可成为业务失败的原因
        print(f"[audit] 写入审计失败 action={action}: {exc}", file=sys.stderr)