import assert from 'node:assert/strict'
import test from 'node:test'
import * as logistics from '../src/utils/logistics.js'

import {
  getContainerProgress,
  getContainerStatus,
  getOceanShipmentCompletion,
  getOceanShipmentQuantity,
  getOceanShipmentStatus,
  getContainerSeaQuantity,
  getRecentReplenishments,
} from '../src/utils/logistics.js'

test('container progress uses the five reference stages and 20 percent per stage', () => {
  assert.deepEqual(getContainerProgress({ stage_seq: 3 }), {
    current: 3,
    percent: 60,
    label: '到港',
    stages: [
      { label: '装柜', percent: 20, color: '#e74c3c', active: true, current: false },
      { label: '开船', percent: 40, color: '#e67e22', active: true, current: false },
      { label: '到港', percent: 60, color: '#f1c40f', active: true, current: true },
      { label: '清关', percent: 80, color: '#7fb84e', active: false, current: false },
      { label: '送仓', percent: 100, color: '#27ae60', active: false, current: false },
    ],
  })
})

test('tracking text recovers an opened-vessel stage when no sequence is stored', () => {
  const progress = getContainerProgress({
    stage_seq: 0,
    status: '在途',
    tracking: '7.27跟进 预计7.31开船/8.1跟进 已开船',
  })

  assert.equal(progress.current, 2)
  assert.equal(progress.percent, 40)
  assert.equal(progress.label, '开船')
})

test('signed containers use the signed state instead of the transit state', () => {
  assert.deepEqual(getContainerStatus({ status: '已签收', actual_in: '8.15' }), {
    label: '已签收',
    tone: 'signed',
  })
})

test('ocean shipment record type distinguishes pending from emitted rows', () => {
  assert.equal(getOceanShipmentStatus({ record_type: 'PENDING', is_done: 1 }), '未发货')
  assert.equal(getOceanShipmentStatus({ record_type: 'EMITTED', is_done: 0 }), '已发货')
})

test('ocean shipment qty2 is labeled by record type instead of sharing one meaning', () => {
  assert.deepEqual(getOceanShipmentQuantity({ record_type: 'PENDING', qty2: 12 }), {
    label: '入库数量',
    value: 12,
  })
  assert.deepEqual(getOceanShipmentQuantity({ record_type: 'EMITTED', qty2: 18 }), {
    label: '发货总数',
    value: 18,
  })
})

test('ocean shipment completion distinguishes false from unknown', () => {
  assert.equal(getOceanShipmentCompletion({ is_done: 1 }), '已完成')
  assert.equal(getOceanShipmentCompletion({ is_done: 0 }), '未完成')
  assert.equal(getOceanShipmentCompletion({ is_done: null }), '未知')
})

test('replenishment records are limited to the latest two months and sorted newest first', () => {
  const rows = [
    { reg_date: '2026-08-13', sea_qty: 1 },
    { reg_date: '2026-08-14', sea_qty: 2 },
    { reg_date: '2026-10-02', sea_qty: 3 },
  ]

  assert.deepEqual(
    getRecentReplenishments(rows, new Date(2026, 9, 14)).map(row => row.sea_qty),
    [3, 2],
  )
})

test('replenishment section data is absent when no records fall within the recent window', () => {
  const rows = [{ reg_date: '2026-07-01', sea_qty: 1 }]

  assert.equal(typeof logistics.getReplenishmentRecordsForDisplay, 'function')
  assert.equal(logistics.getReplenishmentRecordsForDisplay(rows, new Date(2026, 9, 14)), null)
})

test('replenishment section data keeps recent rows for display', () => {
  const row = { reg_date: '2026-10-02', sea_qty: 3 }

  assert.equal(typeof logistics.getReplenishmentRecordsForDisplay, 'function')
  assert.deepEqual(logistics.getReplenishmentRecordsForDisplay([row], new Date(2026, 9, 14)), [row])
})

test('container cards identify the real box number instead of an ordinal label', () => {
  assert.equal(typeof logistics.getContainerIdentifier, 'function')
  assert.equal(logistics.getContainerIdentifier({ container_no: 'FFAU1394874' }), '箱号/柜号：FFAU1394874')
  assert.equal(logistics.getContainerIdentifier({ container_no: '' }), '箱号/柜号：未提供')
})

test('container cards use the API-provided quantity for that container only', () => {
  assert.equal(typeof getContainerSeaQuantity, 'function')
  assert.equal(getContainerSeaQuantity({ sea_qty: 5000 }), 5000)
  assert.equal(getContainerSeaQuantity({ sea_qty: '16800' }), 16800)
  assert.equal(getContainerSeaQuantity({ sea_qty: null }), null)
})
