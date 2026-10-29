export const DEFAULT_DAILY_SALES_SORT = Object.freeze({ sortBy: 'xse', sortOrder: 'desc' })

export function resolveDailySalesSort(sorter, current) {
  const entries = Array.isArray(sorter) ? sorter : [sorter]
  const active = entries.find(entry =>
    ['xse', 'dds'].includes(entry?.columnKey) && ['ascend', 'descend'].includes(entry?.order),
  )

  if (!active) return { ...current }
  return {
    sortBy: active.columnKey,
    sortOrder: active.order === 'ascend' ? 'asc' : 'desc',
  }
}
