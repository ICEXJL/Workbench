const STAGES = ['装柜', '开船', '到港', '清关', '送仓']
const STAGE_COLORS = ['#e74c3c', '#e67e22', '#f1c40f', '#7fb84e', '#27ae60']

export function getContainerProgress(container = {}) {
  const current = resolveContainerStage(container)

  return {
    current,
    percent: current * 20,
    label: STAGES[current - 1],
    stages: STAGES.map((label, index) => ({
      label,
      percent: (index + 1) * 20,
      color: STAGE_COLORS[index],
      active: index < current,
      current: index + 1 === current,
    })),
  }
}

export function getContainerStatus(container = {}) {
  const status = String(container.status || '').trim()
  const normalized = status.toLowerCase()

  if (/已签收|已送仓|已入仓/.test(status) || container.actual_in) {
    return { label: '已签收', tone: 'signed' }
  }
  if (/异常|延误|failed|exception/.test(normalized)) {
    return { label: status || '异常', tone: 'danger' }
  }
  return { label: status === '在途' ? '海运在途' : status || '海运在途', tone: 'transit' }
}

export function getContainerIdentifier(container = {}) {
  const identifier = String(
    container.container_no || container.container_code || container.container || '',
  ).trim()

  return `箱号/柜号：${identifier || '未提供'}`
}

export function getContainerSeaQuantity(container = {}) {
  const value = Number(container?.sea_qty)
  return container?.sea_qty === null || container?.sea_qty === undefined || container?.sea_qty === '' || !Number.isFinite(value)
    ? null
    : value
}

export function getOceanShipmentStatus(shipment = {}) {
  const type = String(shipment.record_type || '').trim().toUpperCase()
  if (['PENDING', '未发货'].includes(type)) return '未发货'
  if (['EMITTED', 'SHIPPED', '已发货', '已出货'].includes(type)) return '已发货'

  return String(shipment.status_raw || shipment.status || '记录类型未知')
}

export function getOceanShipmentQuantity(shipment = {}) {
  const type = String(shipment.record_type || '').trim().toUpperCase()
  const label = ['PENDING', '未发货'].includes(type)
    ? '入库数量'
    : ['EMITTED', 'SHIPPED', '已发货', '已出货'].includes(type)
      ? '发货总数'
      : '数量'

  return { label, value: shipment.qty2 ?? null }
}

export function getOceanShipmentCompletion(shipment = {}) {
  const value = shipment.is_done
  if (value === true || value === 1 || ['1', 'true', '是'].includes(String(value).toLowerCase())) {
    return '已完成'
  }
  if (value === false || value === 0 || ['0', 'false', '否'].includes(String(value).toLowerCase())) {
    return '未完成'
  }
  return '未知'
}

export function getRecentReplenishments(rows = [], now = new Date()) {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const day = today.getDate()
  const cutoff = new Date(today.getFullYear(), today.getMonth(), 1)
  cutoff.setMonth(cutoff.getMonth() - 2)
  const lastDay = new Date(cutoff.getFullYear(), cutoff.getMonth() + 1, 0).getDate()
  cutoff.setDate(Math.min(day, lastDay))

  return rows
    .map((row, index) => ({ row, index, timestamp: parseRecordDate(row?.reg_date) }))
    .filter(entry => entry.timestamp === null || entry.timestamp >= cutoff.getTime())
    .sort((left, right) => {
      if (left.timestamp === null && right.timestamp === null) return left.index - right.index
      if (left.timestamp === null) return 1
      if (right.timestamp === null) return -1
      return right.timestamp - left.timestamp
    })
    .map(entry => entry.row)
}

export function getReplenishmentRecordsForDisplay(rows = [], now = new Date()) {
  const recentRows = getRecentReplenishments(rows, now)
  return recentRows.length ? recentRows : null
}

function resolveContainerStage(container) {
  const sequence = Number(container.stage_seq)
  if (Number.isInteger(sequence) && sequence >= 1 && sequence <= STAGES.length) {
    return sequence
  }

  const stageName = String(container.stage_name || '').trim()
  const namedStage = STAGES.indexOf(stageName)
  if (namedStage >= 0) return namedStage + 1

  const status = String(container.status || '')
  const tracking = String(container.tracking || '').replace(
    /预计[^，。；、\n]*?(开船|开航|到港|抵港|靠港|进港|清关|放行|送仓|入仓|签收)/g,
    '',
  )
  const journey = `${status} ${tracking}`

  if (/已签收|已送仓|已入仓/.test(journey) || container.actual_in) return 5
  if (/已清关|清关完成|查验完成|已放行|放行完成|已提柜|提柜完成|清关完毕/.test(journey)) return 4
  if (/已到港|已抵港|已靠港|已进港/.test(journey)) return 3
  if (/已开船|已开航|已离港|已起运|已出发|开船日期|已上船/.test(journey)) return 2
  return 1
}

function parseRecordDate(value) {
  if (value === null || value === undefined || value === '') return null
  const text = String(value).trim()
  const dateParts = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/.exec(text)
  if (dateParts) {
    const [, year, month, day] = dateParts.map(Number)
    const parsed = new Date(year, month - 1, day)
    return parsed.getFullYear() === year && parsed.getMonth() === month - 1 && parsed.getDate() === day
      ? parsed.getTime()
      : null
  }
  const parsed = Date.parse(text)
  return Number.isFinite(parsed) ? parsed : null
}
