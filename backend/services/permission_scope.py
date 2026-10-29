"""Shared SQL fragments for manager identity aliases and visibility scope."""

MANAGER_ALIAS_FROM_SQL = r"""
FROM operator canonical
JOIN operator alias
  ON alias.real_name LIKE CONCAT(canonical.real_name, '\_%')
WHERE canonical.id=:scope_id
  AND canonical.role='manager'
  AND canonical.real_name NOT LIKE '%\_%'
"""

MANAGER_ALIAS_IDS_SQL = f"SELECT alias.id {MANAGER_ALIAS_FROM_SQL}"
MANAGER_ALIAS_NAMES_SQL = f"SELECT alias.real_name {MANAGER_ALIAS_FROM_SQL}"
MANAGER_IDENTITY_IDS_SQL = f"SELECT :scope_id UNION {MANAGER_ALIAS_IDS_SQL}"
