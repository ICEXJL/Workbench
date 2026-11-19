import assert from 'node:assert/strict'
import test from 'node:test'
const helpers = await import('../src/utils/reportFilters.js')
test('notes visibility excludes blanks and unsubmitted reports', () => {
  assert.equal(typeof helpers.reportsWithAttentionNotes, 'function')
  const rows = [{id:1,attention_notes:'跟进\n补货'}, {id:2,attention_notes:'  \n'}, {id:3}, {id:4,attention_notes:'未提交',submitted:false}]
  assert.deepEqual(helpers.reportsWithAttentionNotes(rows).map(r=>r.id),[1])
})
test('attention card counts unique operators but keeps individual reports', () => {
  assert.equal(typeof helpers.buildAttentionNotesCard, 'function')
  const rows=[{operator_id:1,operator_name:'甲',attention_notes:'a'},{operator_id:1,operator_name:'甲',attention_notes:'b'},{operator_id:2,operator_name:'乙',attention_notes:''}]
  const card=helpers.buildAttentionNotesCard(rows)
  assert.equal(card.issueCount,1)
  assert.equal(card.total,2)
  assert.equal(helpers.buildAttentionNotesCard([{attention_notes:' '}]),null)
})
