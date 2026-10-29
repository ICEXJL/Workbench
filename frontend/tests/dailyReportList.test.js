import assert from 'node:assert/strict'
import test from 'node:test'

let reportFilters = {}
try {
  reportFilters = await import('../src/utils/reportFilters.js')
} catch {}

test('report filters expose department and groups as linked options', () => {
  assert.equal(typeof reportFilters.getDepartmentOptions, 'function')
  assert.equal(typeof reportFilters.getGroupOptions, 'function')

  const people = [
    { id: 1, department: '武汉部', group_name: '一组' },
    { id: 2, department: '武汉部', group_name: '二组' },
    { id: 3, department: '南昌部', group_name: '一组' },
  ]

  assert.deepEqual(reportFilters.getDepartmentOptions(people), ['南昌部', '武汉部'])
  assert.deepEqual(reportFilters.getGroupOptions(people, '武汉部'), ['一组', '二组'])
})

test('report filters narrow operators by department and group', () => {
  assert.equal(typeof reportFilters.filterReportPeople, 'function')

  const people = [
    { id: 1, real_name: '甲', department: '武汉部', group_name: '一组' },
    { id: 2, real_name: '乙', department: '武汉部', group_name: '二组' },
    { id: 3, real_name: '丙', department: '南昌部', group_name: '一组' },
  ]

  assert.deepEqual(
    reportFilters.filterReportPeople(people, { department: '武汉部', group_name: '二组' }).map(person => person.id),
    [2],
  )
})

test('unsubmitted names keep only rows without submission', () => {
  assert.equal(typeof reportFilters.pickUnsubmittedNames, 'function')

  const rows = [
    { operator_name: '甲', submitted: true },
    { operator_name: '乙', submitted: false },
    { operator_name: '丙', submitted: false },
    { operator_name: '', submitted: false },
    { operator_name: '丁', submitted: undefined },
  ]

  assert.deepEqual(reportFilters.pickUnsubmittedNames(rows), ['乙', '丙', '丁'])
})

test('unsubmitted text joins names with a comma', () => {
  assert.equal(typeof reportFilters.buildNameListText, 'function')
  assert.equal(reportFilters.buildNameListText(['甲', '乙']), '甲，乙')
  assert.equal(reportFilters.buildNameListText(['甲', '乙', '丙']), '甲，乙，丙')
  assert.equal(reportFilters.buildNameListText([]), '')
  assert.equal(reportFilters.buildNameListText([null, '甲', '']), '甲')
})

test('unsubmitted text never relies on newlines', () => {
  const text = reportFilters.buildNameListText(['付彤', '何文娟', '何秀丽'])
  assert.ok(!text.includes('\n'), '不应包含换行符，换行在某些粘贴目标里会被吞掉')
  assert.equal(text, '付彤，何文娟，何秀丽')
})
