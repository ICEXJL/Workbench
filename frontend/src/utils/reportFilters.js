/**
 * 日报列表的部门 / 组别筛选工具（纯函数，便于单元测试）。
 *
 * 数据来源是 `/report/people`，每个人的 `department` 和 `group_name`
 * 可能是后端用「、」拼接的多值字符串，例如「武汉一部、深圳一部」。
 * 因此所有比对都必须先拆分再判断，不能用等值匹配。
 */

/** 把「A、B」这类多值字段拆成数组，自动去掉空白项。 */
export function splitMulti(value) {
  return String(value ?? '')
    .split(/[、,，]/)
    .map((part) => part.trim())
    .filter(Boolean)
}

/**
 * 部门选项：全部可见人员的部门去重。
 * 按默认 sort（UTF-16 码点）排序，保证同一批数据顺序稳定。
 */
export function getDepartmentOptions(people = []) {
  const names = new Set()
  people.forEach((person) => {
    splitMulti(person?.department).forEach((name) => names.add(name))
  })
  return [...names].sort()
}

/**
 * 组别选项：指定部门时只返回该部门下的组别，实现「部门 → 组别」联动。
 * department 为空表示不限定部门。
 */
export function getGroupOptions(people = [], department) {
  const names = new Set()
  people
    .filter((person) => !department || splitMulti(person?.department).includes(department))
    .forEach((person) => {
      splitMulti(person?.group_name).forEach((name) => names.add(name))
    })
  return [...names].sort()
}

/**
 * 按部门与组别收窄人员列表，供「运营」下拉使用。
 * group_name 对应 URL 参数 `group`（后端字段叫 group_name）。
 */
export function filterReportPeople(people = [], { department, group_name } = {}) {
  return people.filter((person) => {
    if (department && !splitMulti(person?.department).includes(department)) return false
    if (group_name && !splitMulti(person?.group_name).includes(group_name)) return false
    return true
  })
}

/**
 * 从日报表格行里挑出「未提交」的人员姓名。
 *
 * 用途：日报进度页「未提交日报」卡片双击复制名单。
 * 行数据来自 `displayRows`，其中未提交的行由 `scopedPeople` 补出，
 * 而 `scopedPeople` 已经过权限范围（后端）与部门/组别（前端）双重收窄，
 * 因此这里不需要再判断范围。
 */
export function pickUnsubmittedNames(rows = []) {
  return rows
    .filter((row) => row && !row.submitted)
    .map((row) => row.operator_name)
    .filter(Boolean)
}

/**
 * 把名单拼成可粘贴的文本，人名之间用中文逗号分隔。
 *
 * 2026-10-24 由换行改为逗号：换行符在某些粘贴目标里会被吞掉
 * （单行输入框、部分聊天客户端），导致所有人名连成一串无法辨认。
 * 逗号在任何环境都能保留，也便于后续按逗号拆分。
 */
export function buildNameListText(names = []) {
  return names.filter(Boolean).join('，')
}

export function reportsWithAttentionNotes(rows = []) {
  return rows.filter(row => row && row.submitted !== false && String(row.attention_notes ?? '').trim())
}

export function buildAttentionNotesCard(rows = []) {
  const reports = reportsWithAttentionNotes(rows)
  if (!reports.length) return null
  const issueCount = new Set(reports.map(row => row.operator_id)).size
  const total = new Set(rows.filter(row => row && row.submitted !== false).map(row => row.operator_id)).size
  return {
    key: 'attention_notes', label: '注意事项', issueCount, total,
    ratio: total ? Math.round(issueCount / total * 100) : 0,
    status: '有填写', statusClass: 'normal', issueLabel: '已填写',
  }
}
