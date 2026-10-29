import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import postcss from 'postcss'

let dailySalesSort = {}
try {
  dailySalesSort = await import('../src/utils/dailySalesSort.js')
} catch {}

test('default daily sales sorting ranks sales and then orders descending', () => {
  assert.deepEqual(dailySalesSort.DEFAULT_DAILY_SALES_SORT, { sortBy: 'xse', sortOrder: 'desc' })
})

test('selected table column and direction become API sorting parameters', () => {
  assert.equal(typeof dailySalesSort.resolveDailySalesSort, 'function')
  assert.deepEqual(
    dailySalesSort.resolveDailySalesSort({ columnKey: 'dds', order: 'descend' }, { sortBy: 'xse', sortOrder: 'desc' }),
    { sortBy: 'dds', sortOrder: 'desc' },
  )
})

test('inactive sort events preserve the current API sorting parameters', () => {
  const current = { sortBy: 'xse', sortOrder: 'asc' }

  assert.equal(typeof dailySalesSort.resolveDailySalesSort, 'function')
  assert.deepEqual(dailySalesSort.resolveDailySalesSort({}, current), current)
})

test('multi-sorter events use the active supported metric', () => {
  assert.equal(typeof dailySalesSort.resolveDailySalesSort, 'function')
  assert.deepEqual(
    dailySalesSort.resolveDailySalesSort([
      { columnKey: 'xse', order: null },
      { columnKey: 'dds', order: 'ascend' },
    ], { sortBy: 'xse', sortOrder: 'desc' }),
    { sortBy: 'dds', sortOrder: 'asc' },
  )
})

test('sorted daily sales columns keep the normal header and white body backgrounds', () => {
  const component = readFileSync(new URL('../src/views/dashboard/DailySales.vue', import.meta.url), 'utf8')
  const style = component.match(/<style scoped>([\s\S]*?)<\/style>/)?.[1]
  const rules = postcss.parse(style || '').nodes
  const headerRule = rules.find(rule => rule.selector?.includes('.ant-table-thead > tr > th.ant-table-column-sort'))
  const bodyRule = rules.find(rule => rule.selector?.includes('.ant-table-tbody > tr > td.ant-table-column-sort'))

  assert.ok(headerRule, 'sorted table header should have a local background override')
  assert.ok(bodyRule, 'sorted table body cells should have a local background override')
  assert.equal(headerRule.nodes.find(decl => decl.prop === 'background')?.value, '#f7f9fc')
  assert.equal(bodyRule.nodes.find(decl => decl.prop === 'background')?.value, '#fff')
})
